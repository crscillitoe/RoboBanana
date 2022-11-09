from __future__ import annotations
import asyncio
import logging
import discord
from datetime import datetime, timedelta
from discord import (
    app_commands,
    ButtonStyle,
    Client,
    Embed,
    Intents,
    Interaction,
    Member,
    Message,
    TextStyle,
    SelectOption,
    User,
)
from discord.app_commands.errors import AppCommandError, CheckFailure
from discord.ui import Button, TextInput, Modal, View, Select
import random
from config import Config
from db import DB, RaffleEntry, RaffleType
from db.models import ChannelReward, PredictionEntry

discord.utils.setup_logging(level=logging.INFO, root=True)

STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
WELCOME_CHAT_ID = int(Config.CONFIG["Discord"]["WelcomeChannel"])
PENDING_REWARDS_CHAT_ID = int(Config.CONFIG["Discord"]["PendingRewardChannel"])


class RaffleView(View):
    def __init__(
        self, parent: RaffleEmbed, num_winners: int, raffle_type: RaffleType
    ) -> None:
        super().__init__(timeout=None)

        self.parent = parent
        self.num_winners = num_winners
        self.raffle_type = raffle_type

        self.enter_raffle_button = Button(
            label="Enter Raffle",
            style=ButtonStyle.blurple,
            custom_id="raffle_view:enter_button",
        )
        self.enter_raffle_button.callback = self.enter_raffle_onclick
        self.add_item(self.enter_raffle_button)

        self.end_raffle_button = Button(
            label="End Raffle",
            style=ButtonStyle.red,
            custom_id="raffle_view:end_button",
        )
        self.end_raffle_button.callback = self.end_raffle_onclick
        self.add_item(self.end_raffle_button)

        self.redo_raffle_button = Button(
            label="Redo Raffle",
            style=ButtonStyle.secondary,
            disabled=True,
            custom_id="raffle_view:redo_button",
        )
        self.redo_raffle_button.callback = self.redo_raffle_onclick
        self.add_item(self.redo_raffle_button)

    def has_role(self, role_name: str, interaction: Interaction) -> bool:
        role = discord.utils.get(interaction.user.roles, name=role_name)
        return role is not None

    async def enter_raffle_onclick(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        guild_id = interaction.guild.id
        if not DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.followup.send("This raffle is no longer active!")
            return

        user = interaction.user
        if DB().get_user_raffle_entry(guild_id, user.id) is not None:
            await interaction.followup.send(
                "You have already entered this raffle!", ephemeral=True
            )
            return

        # Mods can always enter a raffle, anyone can enter in "anyone" raffle type
        if (
            not self.has_role("Mod", interaction)
            and self.raffle_type == RaffleType.normal
        ):
            one_week_ago = datetime.now().date() - timedelta(days=6)
            weekly_wins, last_win_entry_dt = DB().get_recent_win_stats(
                guild_id=guild_id, user_id=user.id, after=one_week_ago
            )
            if weekly_wins > 0 and last_win_entry_dt is not None:
                next_eligible_date = last_win_entry_dt.date() + timedelta(days=7)
                next_eligible_ts = int(
                    datetime.combine(
                        next_eligible_date, datetime.min.time()
                    ).timestamp()
                )
                await interaction.followup.send(
                    f"You can only win the raffle once per week. You can next enter on <t:{next_eligible_ts}:D>",
                    ephemeral=True,
                )
                return

        tickets = HoojBot.get_tickets(guild_id, user, self.raffle_type)
        DB().create_raffle_entry(guild_id, user.id, tickets)

        self.parent.update_fields()

        raffle_message_id = DB().get_raffle_message_id(guild_id)
        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        await raffle_message.edit(embed=self.parent)

        await interaction.followup.send(
            f"Raffle entered! Entry Tickets: {tickets}", ephemeral=True
        )

    async def end_raffle_onclick(self, interaction: Interaction):
        if not self.has_role("Mod", interaction):
            await interaction.response.send_message(
                "You must be a mod to do that!", ephemeral=True
            )
            return

        if not DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message("This raffle is no longer active!")
            return

        raffle_message_id = DB().get_raffle_message_id(interaction.guild.id)
        if raffle_message_id is None:
            await interaction.response.send_message(
                "Oops! That raffle does not exist anymore."
            )
            return

        self.enter_raffle_button.disabled = True
        self.end_raffle_button.disabled = True
        self.redo_raffle_button.disabled = False

        end_time = datetime.now()
        self.parent.end_time = int(end_time.timestamp())
        self.parent.update_fields()

        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        await raffle_message.edit(embed=self.parent, view=self)

        await HoojBot._end_raffle_impl(interaction, raffle_message_id, self.num_winners)
        DB().close_raffle(interaction.guild.id, end_time)

    async def redo_raffle_onclick(self, interaction: Interaction):
        if not self.has_role("Mod", interaction):
            await interaction.response.send_message(
                "You must be a mod to do that!", ephemeral=True
            )
            return

        modal = RedoRaffleModal(raffle_message=interaction.message)
        await interaction.response.send_modal(modal)


class RaffleEmbed(Embed):
    def __init__(
        self,
        guild_id: int,
        description: str | None,
        end_time: datetime,
        role_odds: list[tuple[str, int]],
        raffle_type: RaffleType,
    ):
        super().__init__(
            title="VOD Review Raffle",
            description=description,
        )

        self.guild_id = guild_id
        self.raffle_type = raffle_type
        self.end_time = int(end_time.timestamp())

        # global odds
        global_odds_str_parts = ["Everyone: +100 Tickets"]
        if self.raffle_type == RaffleType.normal:
            global_odds_str_parts += [
                "Bad Luck Protection*: +5 Tickets",
                "",
                "*\*Per consecutive loss, resets when you win.*",
            ]
        self.global_odds_str = "\n".join(global_odds_str_parts)

        # role odds
        self.role_odds_str = "\n".join(
            f"{name}: {'+' if mod > 0 else '-'}{mod} Tickets" for name, mod in role_odds
        )

        self.update_fields()

    def update_fields(self) -> None:
        self.clear_fields()
        self.add_field(name="Raffle End", value=f"<t:{self.end_time}:R>", inline=True)
        self.add_field(
            name="Entries",
            value=str(DB().get_raffle_entry_count(self.guild_id)),
            inline=True,
        )
        self.add_field(
            name="Total Tickets", value=str(self.get_raffle_tickets()), inline=True
        )
        self.add_field(name="Global Odds", value=self.global_odds_str, inline=True)
        self.add_field(name="Role Odds", value=self.role_odds_str, inline=True)

    def get_raffle_tickets(self) -> int:
        entries = DB().get_raffle_entries(self.guild_id)
        return sum([e.tickets for e in entries])


class NewRaffleModal(Modal, title="Create VOD Review Raffle"):
    def __init__(self, raffle_type: RaffleType) -> None:
        super().__init__(timeout=None)

        self.raffle_type = raffle_type

        self.duration = TextInput(
            label="Duration (in seconds)",
            default="120",
            style=TextStyle.short,
            required=True,
            min_length=1,
        )
        self.num_winners = TextInput(
            label="Number of Winners",
            default="1",
            placeholder="How many winners to draw at the end (Must be an integer > 0)",
            style=TextStyle.short,
            required=True,
            min_length=1,
            max_length=2,
        )
        self.description = TextInput(
            label="Description",
            placeholder="Description",
            default="Raffle time! Click below to enter. The winner(s) will be randomly chosen.",
            style=TextStyle.paragraph,
            required=False,
        )

        self.add_item(self.duration)
        self.add_item(self.num_winners)
        self.add_item(self.description)

    async def on_submit(self, interaction: Interaction) -> None:
        # validate inputs
        try:
            duration = int(self.duration.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid raffle duration.", ephemeral=True
            )
            return

        try:
            num_winners = int(self.num_winners.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid number of winners.", ephemeral=True
            )
            return

        description = self.description.value
        guild_role_names = {r.id: r.name for r in interaction.guild.roles}
        role_modifiers = DB().get_role_modifiers(interaction.guild.id)
        role_odds = [
            (guild_role_names[_id], m) for _id, m in role_modifiers.items() if m != 0
        ]

        end_time = datetime.now() + timedelta(seconds=duration)

        embed = RaffleEmbed(
            guild_id=interaction.guild.id,
            description=description,
            end_time=end_time,
            role_odds=role_odds,
            raffle_type=self.raffle_type,
        )
        view = RaffleView(
            parent=embed, num_winners=num_winners, raffle_type=self.raffle_type
        )
        await interaction.response.send_message("Creating raffle...")
        raffle_message = await interaction.original_response()

        DB().create_raffle(
            guild_id=interaction.guild.id,
            message_id=raffle_message.id,
            raffle_type=self.raffle_type,
        )

        await raffle_message.edit(content="", embed=embed, view=view)


class RedoRaffleModal(Modal, title="Redo Raffle"):
    def __init__(self, raffle_message: Message) -> None:
        super().__init__(timeout=None)

        self.raffle_message = raffle_message

        self.num_winners = TextInput(
            label="Number of Winners",
            default="1",
            placeholder="How many winners to draw (Must be an integer > 0)",
            style=TextStyle.short,
            required=True,
            min_length=1,
            max_length=2,
        )

        self.add_item(self.num_winners)

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            num_winners = int(self.num_winners.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid number of winners.", ephemeral=True
            )
            return

        DB().clear_win(self.raffle_message.id)

        await HoojBot._end_raffle_impl(interaction, self.raffle_message.id, num_winners)

        DB().close_raffle(interaction.guild.id, end_time=datetime.now())


class AddRewardModal(Modal, title="Add new channel reward"):
    def __init__(self):
        super().__init__(timeout=None)
        self.name = TextInput(
            label="Name",
            placeholder="Name of new channel reward",
            required=True,
        )
        self.point_cost = TextInput(
            label="Point Cost",
            placeholder="The number of points required to redeem this reward",
            required=True,
            style=TextStyle.short,
            min_length=1,
        )

        self.add_item(self.name)
        self.add_item(self.point_cost)

    async def on_submit(self, interaction: Interaction):
        try:
            point_cost = int(self.point_cost.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid point cost for reward.", ephemeral=True
            )
            return

        DB().add_channel_reward(self.name.value, point_cost)
        await interaction.response.send_message(f"New reward added!", ephemeral=True)


class CreatePredictionModal(Modal, title="Start new prediction"):
    def __init__(self):
        super().__init__(timeout=None)
        self.description = TextInput(
            label="Description",
            placeholder="What are viewers trying to predict?",
            required=True,
        )
        self.option_one = TextInput(
            label="Option 1",
            placeholder="BELIEF",
            required=True,
        )
        self.option_two = TextInput(
            label="Option 2",
            placeholder="DOUBT",
            required=True,
        )
        self.duration = TextInput(
            label="Duration (in seconds)",
            default="120",
            style=TextStyle.short,
            required=True,
            min_length=1,
        )

        self.add_item(self.description)
        self.add_item(self.option_one)
        self.add_item(self.option_two)
        self.add_item(self.duration)

    async def on_submit(self, interaction: Interaction):
        try:
            duration = int(self.duration.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid prediction duration.", ephemeral=True
            )
            return
        await interaction.response.send_message("Creating prediction...")

        end_time = datetime.now() + timedelta(seconds=duration)
        prediction_message = await interaction.original_response()
        DB().create_prediction(
            interaction.guild_id,
            prediction_message.id,
            self.description.value,
            self.option_one.value,
            self.option_two.value,
            end_time,
        )
        prediction_embed = PredictionEmbed(
            interaction.guild_id, self.description.value, end_time
        )
        prediction_view = PredictionView(
            prediction_embed, self.option_one.value, self.option_two.value
        )
        await prediction_message.edit(
            content="", embed=prediction_embed, view=prediction_view
        )


class PredictionVoteModal(Modal, title="Cast your vote!"):
    def __init__(self, parent: PredictionEmbed, guess: int, point_balance: int):
        super().__init__(timeout=None)
        self.guess = guess
        self.parent = parent
        self.point_balance = point_balance
        self.channel_points = TextInput(
            label=f"Channel Points ({point_balance})",
            placeholder="50",
            style=TextStyle.short,
            min_length=1,
            required=True,
        )
        self.add_item(self.channel_points)

    async def on_submit(self, interaction: Interaction):
        try:
            channel_points = int(self.channel_points.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid point value", ephemeral=True
            )
            return

        if channel_points > self.point_balance:
            return await interaction.response.send_message(
                f"You can only wager up to {self.point_balance} points", ephemeral=True
            )

        result, _ = DB().withdraw_points(interaction.user.id, channel_points)
        if not result:
            return await interaction.response.send_message(
                "Unable to cast vote - please try again!", ephemeral=True
            )

        DB().create_prediction_entry(
            interaction.guild_id, interaction.user.id, channel_points, self.guess
        )
        self.parent.update_fields()

        prediction_message_id = DB().get_prediction_message_id(interaction.guild_id)
        prediction_message = await interaction.channel.fetch_message(
            prediction_message_id
        )
        await prediction_message.edit(embed=self.parent)

        await interaction.response.send_message(
            f"Vote cast with {channel_points} points!", ephemeral=True
        )


class PredictionEmbed(Embed):
    def __init__(
        self,
        guild_id: int,
        description: str,
        end_time: datetime,
    ):
        super().__init__(
            title="Prediction!",
            description=description,
        )

        self.guild_id = guild_id
        self.end_time = int(end_time.timestamp())

        self.update_fields()

    def update_fields(self) -> None:
        self.clear_fields()
        self.add_field(
            name="Prediction End", value=f"<t:{self.end_time}:R>", inline=True
        )
        option_one_points, option_two_points = DB().get_prediction_point_counts(
            self.guild_id
        )
        total_points = option_one_points + option_two_points
        if total_points == 0:
            total_points = 1

        option_one_percent = round((option_one_points / total_points) * 100, 1)
        option_two_percent = 100 - option_one_percent

        self.add_field(
            name="Option One Points",
            value=f"{option_one_points} ({option_one_percent}%)",
            inline=True,
        )
        self.add_field(
            name="Option Two Points",
            value=f"{option_two_points} ({option_two_percent}%)",
            inline=True,
        )


class PredictionView(View):
    def __init__(
        self, parent: PredictionEmbed, option_one: str, option_two: str
    ) -> None:
        super().__init__(timeout=None)

        self.parent = parent

        self.vote_one_button = Button(
            label=option_one,
            style=ButtonStyle.blurple,
            custom_id="prediction_view:vote_one_button",
        )
        self.vote_one_button.callback = self.vote_one_button_onclick
        self.add_item(self.vote_one_button)

        self.vote_two_button = Button(
            label=option_two,
            style=ButtonStyle.secondary,
            custom_id="prediction_view:vote_two_button",
        )
        self.vote_two_button.callback = self.vote_two_button_onclick
        self.add_item(self.vote_two_button)

        self.end_prediction_button = Button(
            label="End Prediction",
            style=ButtonStyle.red,
            custom_id="prediction_view:end_prediction_button",
        )
        self.end_prediction_button.callback = self.end_prediction_button_onclick
        self.add_item(self.end_prediction_button)

    async def user_eligible(self, interaction: Interaction) -> bool:
        entry = DB().get_user_prediction_entry(
            interaction.guild_id, interaction.user.id
        )
        if entry is not None:
            await interaction.response.send_message(
                "You have already entered the prediction!", ephemeral=True
            )
            return False

        if not DB().accepting_prediction_entries(interaction.guild_id):
            await interaction.response.send_message(
                "Prediction has been closed!", ephemeral=True
            )
            return False
        return True

    def has_role(self, role_name: str, interaction: Interaction) -> bool:
        role = discord.utils.get(interaction.user.roles, name=role_name)
        return role is not None

    async def end_prediction_button_onclick(self, interaction: Interaction):
        if not self.has_role("Mod", interaction):
            interaction.response.send_message(
                "You must be a mod to do that!", ephemeral=True
            )

        DB().close_prediction(interaction.guild_id)
        self.parent.update_fields()

        self.vote_one_button.disabled = True
        self.vote_two_button.disabled = True
        self.end_prediction_button.disabled = True

        prediction_message_id = DB().get_prediction_message_id(interaction.guild_id)
        prediction_message = await interaction.channel.fetch_message(
            prediction_message_id
        )
        await prediction_message.edit(embed=self.parent, view=self)

        await interaction.response.send_message("Prediction closed!")

    async def vote_one_button_onclick(self, interaction: Interaction):
        if not await self.user_eligible(interaction):
            return
        point_balance = DB().get_point_balance(interaction.user.id)
        modal = PredictionVoteModal(self.parent, 0, point_balance)
        await interaction.response.send_modal(modal)

    async def vote_two_button_onclick(self, interaction: Interaction):
        if not await self.user_eligible(interaction):
            return
        point_balance = DB().get_point_balance(interaction.user.id)
        modal = PredictionVoteModal(self.parent, 1, point_balance)
        await interaction.response.send_modal(modal)


class RedeemRewardView(View):
    def __init__(
        self, user_points: int, channel_rewards: list[ChannelReward], client: Client
    ):
        super().__init__(timeout=None)
        self.options = []
        self.client = client
        self.user_points = user_points
        self.reward_lookup = {
            channel_reward.id: channel_reward for channel_reward in channel_rewards
        }
        for channel_reward in channel_rewards:
            # Only display options the user can afford
            if channel_reward.point_cost > user_points:
                continue

            self.options.append(
                SelectOption(
                    label=f"({channel_reward.point_cost}) {channel_reward.name}",
                    value=channel_reward.id,
                )
            )
        self.select = Select(placeholder="Reward to redeem", options=self.options)

        self.add_item(self.select)

    async def interaction_check(self, interaction: Interaction):
        redeemed_reward = self.reward_lookup.get(int(self.select.values[0]))
        if redeemed_reward is None:
            return await interaction.response.send_message(
                "Invalid reward redeemed", ephemeral=True
            )
        if redeemed_reward.point_cost > self.user_points:
            return await interaction.response.send_message(
                "Not enough channel points to redeem this reward - try again later!",
                ephemeral=True,
            )

        success, balance = DB().withdraw_points(
            interaction.user.id, redeemed_reward.point_cost
        )
        if not success:
            return await interaction.response.send_message(
                "Failed to redeem reward - please try again.", ephemeral=True
            )

        await interaction.response.send_message(
            f"Redeemed! You have {balance} points remaining.", ephemeral=True
        )
        await self.client.get_channel(STREAM_CHAT_ID).send(
            f"{interaction.user.mention} redeemed {redeemed_reward.name}!"
        )

        pending_reward_view = PendingReward(
            redeemed_reward, interaction.user, self.client
        )
        await self.client.get_channel(PENDING_REWARDS_CHAT_ID).send(
            f"Pending {redeemed_reward.name} for {interaction.user.mention}",
            view=pending_reward_view,
        )


class PendingReward(View):
    def __init__(self, reward: ChannelReward, user: User, client: Client) -> None:
        super().__init__(timeout=None)

        self.reward = reward
        self.user = user
        self.client = client

        self.complete_reward_button = Button(
            label="Complete reward",
            style=ButtonStyle.blurple,
            custom_id="pending_reward_view:complete_button",
        )
        self.complete_reward_button.callback = self.complete_reward_onclick
        self.add_item(self.complete_reward_button)

        self.refund_reward_button = Button(
            label="Refund reward",
            style=ButtonStyle.red,
            custom_id="pending_reward_view:refund_button",
        )
        self.refund_reward_button.callback = self.refund_reward_onclick
        self.add_item(self.refund_reward_button)

    async def complete_reward_onclick(self, interaction: Interaction):
        self.complete_reward_button.disabled = True
        self.refund_reward_button.disabled = True
        await self.client.get_channel(STREAM_CHAT_ID).send(
            f"Completed reward for {self.user.mention}"
        )

        await interaction.response.send_message(
            f"Reward completed for {self.user.mention}"
        )
        await interaction.message.edit(content="Reward no longer pending", view=self)

    async def refund_reward_onclick(self, interaction: Interaction):
        success, _ = DB().deposit_points(self.user.id, self.reward.point_cost)
        if not success:
            return await interaction.response.send_message(
                f"Failed to refund points to {self.user.mention} - please try again.",
                ephemeral=True,
            )

        await self.client.get_channel(STREAM_CHAT_ID).send(
            f"Refunded reward for {self.user.mention}"
        )

        self.complete_reward_button.disabled = True
        self.refund_reward_button.disabled = True
        await interaction.message.edit(content="Reward no longer pending", view=self)

        await interaction.response.send_message(
            f"Refunded {self.reward.point_cost} points for {self.user.mention}",
            ephemeral=True,
        )


class RaffleBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True

        super().__init__(intents=intents)

    async def on_ready(self):
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")
        guild = discord.Object(id=1037471015216885791)
        tree.clear_commands(guild=guild)
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)

    async def on_button_click(self, interaction):
        logging.info(f"button clicked: {interaction}")

    async def on_message(self, message: Message):
        # Don't respond to ourselves
        if message.author == self.user:
            return
        # Only look in the active stream channel
        channels_to_listen_to = {STREAM_CHAT_ID, WELCOME_CHAT_ID}
        if message.channel.id not in channels_to_listen_to:
            return

        if message.channel.id == STREAM_CHAT_ID:
            DB().accrue_channel_points(message.author.id, message.author.roles)

        if message.channel.id == WELCOME_CHAT_ID:
            premium_ids = map(
                int,
                [
                    Config.CONFIG["Discord"]["Tier1RoleID"],
                    Config.CONFIG["Discord"]["Tier2RoleID"],
                    Config.CONFIG["Discord"]["Tier3RoleID"],
                ],
            )

            role_name = None
            for role_id in premium_ids:
                role = discord.utils.get(message.author.roles, id=role_id)
                if role is not None:
                    role_name = role.name
                    break

            if role_name is not None:
                await self.get_channel(STREAM_CHAT_ID).send(
                    f"Thank you {message.author.mention} for joining {role_name}!"
                )


client = RaffleBot()
tree = app_commands.CommandTree(client)


@client.event
async def on_guild_join(guild):
    tree.clear_commands(guild=guild)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)


@app_commands.guild_only()
class HoojBot(app_commands.Group, name="hooj"):
    def __init__(self, tree: app_commands.CommandTree) -> None:
        super().__init__()
        self.tree = tree

    @staticmethod
    def check_owner(interaction: Interaction) -> bool:
        return interaction.user.id == 112386674155122688

    @staticmethod
    def check_hooj(interaction: Interaction) -> bool:
        return interaction.user.id == 82969926125490176

    async def on_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, CheckFailure):
            return await interaction.response.send_message(
                "Failed to perform command - please verify permissions.", ephemeral=True
            )
        super().on_error()

    @app_commands.command(name="sync")
    @app_commands.check(check_owner)
    @app_commands.checks.has_role("Mod")
    async def sync(self, interaction: Interaction) -> None:
        """Manually sync slash commands to guild"""

        guild = interaction.guild
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        await interaction.response.send_message("Commands synced", ephemeral=True)

    @app_commands.command(name="start")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(raffle_type="Raffle Type (default: normal)")
    async def start(
        self, interaction: Interaction, raffle_type: RaffleType = RaffleType.normal
    ):
        """Starts a new raffle"""

        if DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message(
                "There is already an ongoing raffle!"
            )
            return

        modal = NewRaffleModal(raffle_type=raffle_type)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="end")
    @app_commands.checks.has_role("Mod")
    async def end(
        self,
        interaction: Interaction,
        num_winners: int = 1,
    ) -> None:
        """Closes an existing raffle and pick the winner(s)"""

        if not DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message(
                "There is no ongoing raffle! You need to start a new one."
            )
            return

        raffle_message_id = DB().get_raffle_message_id(interaction.guild.id)
        if raffle_message_id is None:
            await interaction.response.send_message(
                "Oops! That raffle does not exist anymore."
            )
            return

        await HoojBot._end_raffle_impl(interaction, raffle_message_id, num_winners)
        DB().close_raffle(interaction.guild.id, end_time=datetime.now())

    @app_commands.command(name="add_reward")
    @app_commands.checks.has_role("Mod")
    async def add_reward(self, interaction: Interaction):
        """Creates new channel reward for redemption"""
        modal = AddRewardModal()
        await interaction.response.send_modal(modal)

    @app_commands.command(name="remove_reward")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(name="Name of reward to remove")
    async def remove_reward(self, interaction: Interaction, name: str):
        """Removes channel reward for redemption"""
        DB().remove_channel_reward(name)
        await interaction.response.send_message(
            f"Successfully removed {name}!", ephemeral=True
        )

    @app_commands.command(name="redeem")
    async def redeem_reward(self, interaction: Interaction):
        """Redeem an available channel reward"""
        redemptions_allowed = DB().check_redemption_status()
        if not redemptions_allowed:
            return await interaction.response.send_message(
                "Sorry! Reward redemptions are currently paused. Try again during stream!",
                ephemeral=True,
            )

        rewards = DB().get_channel_rewards()
        user_points = DB().get_point_balance(interaction.user.id)
        view = RedeemRewardView(user_points, rewards, client)
        await interaction.response.send_message(
            f"You currently have {user_points} points", view=view, ephemeral=True
        )

    @app_commands.command(name="list_rewards")
    async def list_rewards(self, interaction: Interaction):
        """List all available channel rewards"""
        rewards = DB().get_channel_rewards()
        return_message = "The rewards currently available to redeem are:\n\n"
        for reward in rewards:
            return_message += f"({reward.point_cost}) {reward.name}\n"
        await interaction.response.send_message(return_message, ephemeral=True)

    @app_commands.command(name="allow_redemptions")
    @app_commands.checks.has_role("Mod")
    async def allow_redemptions(self, interaction: Interaction):
        """Allow rewards to be redeemed"""
        DB().allow_redemptions()
        await interaction.response.send_message(
            "Redemptions are now enabled", ephemeral=True
        )

    @app_commands.command(name="pause_redemptions")
    @app_commands.checks.has_role("Mod")
    async def pause_redemptions(self, interaction: Interaction):
        """Pause rewards from being redeemed"""
        DB().pause_redemptions()
        await interaction.response.send_message("Redemptions are now paused", ephemeral=True)

    @app_commands.command(name="check_redemption_status")
    async def check_redemption_status(self, interaction: Interaction):
        """Check whether or not rewards are eligible to be redeemed"""
        status = DB().check_redemption_status()
        status_message = "allowed" if status else "paused"
        await interaction.response.send_message(
            f"Redemptions are currently {status_message}."
        )

    @app_commands.command(name="point_balance")
    async def point_balance(self, interaction: Interaction):
        """Get your current number of channel points"""
        user_points = DB().get_point_balance(interaction.user.id)
        await interaction.response.send_message(
            f"You currently have {user_points} points", ephemeral=True
        )

    @app_commands.command(name="give_points")
    @app_commands.check(check_hooj)
    @app_commands.describe(user="User ID to award points")
    @app_commands.describe(points="Number of points to award")
    async def give_points(self, interaction: Interaction, user: User, points: int):
        """Manually give points to user"""
        success, _ = DB().deposit_points(user.id, points)
        if not success:
            return await interaction.response.send_message(
                f"Failed to award points - please try again.", ephemeral=True
            )
        await interaction.response.send_message(
            "Successfully awarded points!", ephemeral=True
        )

    @app_commands.command(name="start_prediction")
    @app_commands.checks.has_role("Mod")
    async def start_prediction(self, interaction: Interaction):
        if DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "There is already an ongoing prediction!", ephemeral=True
            )
        await interaction.response.send_modal(CreatePredictionModal())

    @app_commands.command(name="payout_prediction")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(option="Option to payout")
    async def payout_prediction(self, interaction: Interaction, option: int):
        if not DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "No ongoing prediction!", ephemeral=True
            )

        option_one, option_two = DB().get_prediction_point_counts(interaction.guild_id)
        total_points = option_one + option_two
        winning_pot = option_one if option == 0 else option_two
        entries: list[PredictionEntry] = DB().get_prediction_entries_for_guess(
            interaction.guild_id, option
        )

        for entry in entries:
            pot_percentage = entry.channel_points / winning_pot
            payout = round(total_points * pot_percentage)
            DB().deposit_points(entry.user_id, payout)

        DB().complete_prediction(interaction.guild_id)
        await interaction.response.send_message(
            f"Payout complete! {total_points} distributed.", ephemeral=True
        )

    @staticmethod
    async def _end_raffle_impl(
        interaction: Interaction,
        raffle_message_id: int,
        num_winners: int,
    ) -> None:
        if num_winners == 0:
            await interaction.response.send_message("There is no winner.")
            return

        guild_id = interaction.guild.id
        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        if raffle_message is None:
            raise Exception("Oops! That raffle does not exist anymore.")

        await interaction.response.defer(thinking=True)

        raffle_entries = DB().get_raffle_entries(guild_id)
        if len(raffle_entries) == 0:
            await interaction.followup.send("No one is elligble to win the raffle.")
            return

        winner_ids = HoojBot.choose_winners(raffle_entries, num_winners)
        winners = [interaction.guild.get_member(_id) for _id in winner_ids]

        if len(winners) == 1:
            await interaction.followup.send(f"{winners[0].mention} has won the raffle!")
        else:
            await interaction.followup.send(
                f"Raffle winners are: {', '.join(w.mention for w in winners)}!"
            )

        DB().record_win(guild_id, winner_ids)

    @staticmethod
    def choose_winners(entries: list[RaffleEntry], num_winners: int) -> list[int]:
        """
        Every raffle entry has a ticket count, which is their entry weight.

        Then we let random.choices work its magic.
        """
        if len(entries) < num_winners:
            raise Exception("There are not enough entries for that many winners.")

        # step 1. convert raffle entries into lists of user_ids and tickets
        entrants = []
        entrant_weights = []
        for ent in entries:
            entrants.append(ent.user_id)
            entrant_weights.append(ent.tickets)

        # step 3. using weighted probability (without replacement), select the random winner(s)
        winners = HoojBot.weighted_sample_without_replacement(
            population=entrants, weights=entrant_weights, k=num_winners
        )

        return winners

    # h/t https://maxhalford.github.io/blog/weighted-sampling-without-replacement/
    @staticmethod
    def weighted_sample_without_replacement(population, weights, k):
        v = [random.random() ** (1 / w) for w in weights]
        order = sorted(range(len(population)), key=lambda i: v[i])
        return [population[i] for i in order[-k:]]

    @staticmethod
    def get_tickets(guild_id: int, user: Member, raffle_type: RaffleType) -> int:
        """
        Calculate the number of tickers a specific user should have for a raffle entry.
        """
        # every entrant starts with 100 ticket
        tickets = 100

        # + any role modifiers from the DB
        role_modifiers = DB().get_role_modifiers(guild_id)
        tickets += sum(role_modifiers.get(r.id, 0) for r in user.roles)

        # add bad luck protection for normal raffles
        if raffle_type == RaffleType.normal:
            # + 5tk/loss since last win
            loss_streak = DB().get_loss_streak_for_user(user.id)
            tickets += 5 * loss_streak

        return tickets


async def main():
    async with client:
        tree.add_command(HoojBot(tree))
        await client.start(Config.CONFIG["Discord"]["Token"])


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations
import asyncio
import logging
import discord
from datetime import datetime
from discord import (
    app_commands,
    Client,
    Intents,
    Interaction,
    Message,
    User,
)
from discord.app_commands.errors import AppCommandError, CheckFailure
from config import Config
from controllers.raffle_controller import RaffleController
from db import DB, RaffleType
from db.models import PredictionEntry
from views.predictions.create_predictions_modal import CreatePredictionModal
from views.raffle.new_raffle_modal import NewRaffleModal
from views.rewards.add_reward_modal import AddRewardModal
from views.rewards.redeem_reward_view import RedeemRewardView

discord.utils.setup_logging(level=logging.INFO, root=True)

STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
WELCOME_CHAT_ID = int(Config.CONFIG["Discord"]["WelcomeChannel"])
PENDING_REWARDS_CHAT_ID = int(Config.CONFIG["Discord"]["PendingRewardChannel"])
GUILD_ID = int(Config.CONFIG["Discord"]["GuildID"])

JOEL_DISCORD_ID = 112386674155122688
HOOJ_DISCORD_ID = 1037471015216885791


class RaffleBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True

        super().__init__(intents=intents)

    async def on_ready(self):
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")
        guild = discord.Object(id=GUILD_ID)
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
        return interaction.user.id == JOEL_DISCORD_ID

    @staticmethod
    def check_hooj(interaction: Interaction) -> bool:
        return interaction.user.id == HOOJ_DISCORD_ID

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

        await RaffleController._end_raffle_impl(
            interaction, raffle_message_id, num_winners
        )
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
        await interaction.response.send_message(
            "Redemptions are now paused", ephemeral=True
        )

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

    @app_commands.command(name="refund_prediction")
    @app_commands.checks.has_role("Mod")
    async def refund_prediction(self, interaction: Interaction):
        if not DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "No ongoing prediction!", ephemeral=True
            )

        if DB().accepting_prediction_entries(interaction.guild_id):
            return await interaction.response.send_message(
                "Please close prediction from entries before refunding!", ephemeral=True
            )

        option_one_entries = DB().get_prediction_entries_for_guess(
            interaction.guild_id, 0
        )

        option_two_entries = DB().get_prediction_entries_for_guess(
            interaction.guild_id, 1
        )

        entries = option_one_entries + option_two_entries
        for entry in entries:
            DB().deposit_points(entry.user_id, entry.channel_points)

        DB().complete_prediction(interaction.guild_id)
        await interaction.response.send_message(
            "Prediction has been refunded!", ephemeral=True
        )

    @app_commands.command(name="payout_prediction")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(option="Option to payout")
    async def payout_prediction(self, interaction: Interaction, option: int):
        if not DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "No ongoing prediction!", ephemeral=True
            )

        if DB().accepting_prediction_entries(interaction.guild_id):
            return await interaction.response.send_message(
                "Please close prediction from entries before paying out!",
                ephemeral=True,
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


async def main():
    async with client:
        tree.add_command(HoojBot(tree))
        await client.start(Config.CONFIG["Discord"]["Token"])


if __name__ == "__main__":
    asyncio.run(main())

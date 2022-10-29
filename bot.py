from __future__ import annotations
import asyncio
import logging
import discord
from datetime import datetime, timedelta
from discord import app_commands, ButtonStyle, Client, Embed, Intents, Interaction, Member, Message, TextStyle
from discord.ui import Button, TextInput, Modal, View
import random
from config import Config
from db import DB

discord.utils.setup_logging(level=logging.INFO, root=True)

intents = Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

client = Client(intents=intents)
tree = app_commands.CommandTree(client)

class RaffleView(View):
    def __init__(self, parent: RaffleEmbed, num_winners: int) -> None:
        super().__init__(timeout=None)

        self.parent = parent
        self.num_winners = num_winners

        self.enter_raffle_button = Button(label="Enter Raffle", style=ButtonStyle.blurple)
        self.enter_raffle_button.callback = self.enter_raffle_onclick
        self.add_item(self.enter_raffle_button)

        self.end_raffle_button = Button(label="End Raffle", style=ButtonStyle.red)
        self.end_raffle_button.callback = self.end_raffle_onclick
        self.add_item(self.end_raffle_button)

        self.redo_raffle_button = Button(label="Redo Raffle", style=ButtonStyle.secondary, disabled=True)
        self.redo_raffle_button.callback = self.redo_raffle_onclick
        self.add_item(self.redo_raffle_button)

    def has_role(self, role_name: str, interaction: Interaction) -> bool:
        role = discord.utils.get(interaction.user.roles, name=role_name)
        return role is not None

    async def enter_raffle_onclick(self, interaction: Interaction):
        guild_id = interaction.guild.id
        user = interaction.user
        if DB().get_user_raffle_entry(guild_id, user.id) is not None:
            await interaction.response.send_message("You have already entered this raffle!", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        tickets = RaffleCog.get_tickets(guild_id, user)
        DB().create_raffle_entry(guild_id, user.id, tickets)

        self.parent.update_fields()

        raffle_message_id = DB().get_raffle_message_id(guild_id)
        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        await raffle_message.edit(embed=self.parent)

        await interaction.followup.send(f"Raffle entered! Entry Tickets: {tickets}", ephemeral=True)

    async def end_raffle_onclick(self, interaction: Interaction):
        if not self.has_role("Mod", interaction):
            await interaction.response.send_message("You must be a mod to do that!", ephemeral=True)
            return

        if not DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message("This raffle is no longer active!")
            return

        raffle_message_id = DB().get_raffle_message_id(interaction.guild.id)
        if raffle_message_id is None:
            await interaction.response.send_message("Oops! That raffle does not exist anymore.")
            return

        self.enter_raffle_button.disabled = True
        self.end_raffle_button.disabled = True
        self.redo_raffle_button.disabled = False

        end_time = datetime.now()
        self.parent.end_time = int(end_time.timestamp())
        self.parent.update_fields()

        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        await raffle_message.edit(embed=self.parent, view=self)

        await RaffleCog._end_raffle_impl(interaction, raffle_message_id, self.num_winners)
        DB().close_raffle(interaction.guild.id, end_time)


    async def redo_raffle_onclick(self, interaction: Interaction):
        if not self.has_role("Mod", interaction):
            await interaction.response.send_message("You must be a mod to do that!", ephemeral=True)
            return

        modal = RedoRaffleModal(raffle_message=interaction.message)
        await interaction.response.send_modal(modal)

class RaffleEmbed(Embed):
    def __init__(self,
        guild_id: int,
        description: str | None,
        num_winners: int,
        duration: int,
        role_odds: list[tuple[str, int]],
    ):
        super().__init__(
            title="VOD Review Raffle",
            description=description,
        )

        self.guild_id = guild_id
        self.buttons_view = RaffleView(parent=self, num_winners=num_winners)
        self.end_time = int((datetime.now() + timedelta(seconds=duration)).timestamp())
        self.role_odds = role_odds

        self.update_fields()

    def update_fields(self) -> None:
        self.clear_fields()
        self.add_field(name="Raffle End", value=f"<t:{self.end_time}:R>", inline=True)
        self.add_field(name="Entries", value=str(DB().get_raffle_entry_count(self.guild_id)), inline=True)
        self.add_field(name="Total Tickets", value=str(self.get_raffle_tickets()), inline=True)
        self.add_field(name="Odds", value=self.get_role_odds_string(), inline=True)

    def get_raffle_tickets(self) -> int:
        entries = DB().get_raffle_entries(self.guild_id)
        return sum([e.tickets for e in entries])

    def get_role_odds_string(self) -> str:
        return "\n".join(
            f"{name}: {'+' if mod > 0 else '-'}{mod} Tickets" for name, mod in self.role_odds
        )

class NewRaffleModal(Modal, title="Create VOD Review Raffle"):
    def __init__(self) -> None:
        super().__init__(timeout=None)

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
            max_length=2
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
            await interaction.response.send_message('Invalid raffle duration.', ephemeral=True)
            return

        try:
            num_winners = int(self.num_winners.value)
        except ValueError:
            await interaction.response.send_message('Invalid number of winners.', ephemeral=True)
            return

        description = self.description.value
        guild_role_names = {r.id: r.name for r in interaction.guild.roles}
        role_modifiers = DB().get_role_modifiers(interaction.guild.id)
        role_odds = [
            ('Everyone', 100)
        ] + [(guild_role_names[_id], m) for _id, m in role_modifiers.items() if m != 0]

        embed = RaffleEmbed(
            guild_id=interaction.guild.id,
            description=description,
            num_winners=num_winners,
            duration=duration,
            role_odds=role_odds,
        )
        await interaction.response.send_message(embed=embed, view=embed.buttons_view)
        raffle_message = await interaction.original_response()

        DB().create_raffle(interaction.guild.id, raffle_message.id)



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
            max_length=2
        )

        self.add_item(self.num_winners)

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            num_winners = int(self.num_winners.value)
        except ValueError:
            await interaction.response.send_message('Invalid number of winners.', ephemeral=True)
            return

        DB().clear_win(self.raffle_message.id)

        await RaffleCog._end_raffle_impl(interaction, self.raffle_message.id, num_winners)

        DB().close_raffle(interaction.guild.id, end_time=datetime.now())


@app_commands.guild_only()
class RaffleCog(app_commands.Group, name="raffle"):
    def __init__(self, tree: app_commands.CommandTree) -> None:
        super().__init__()
        self.tree = tree

    @staticmethod
    def check_owner(interaction: Interaction) -> bool:
        return interaction.user.id == 112386674155122688

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
    async def start(self, interaction: Interaction):
        """Starts a new raffle"""

        if DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message("There is already an ongoing raffle!")
            return

        modal = NewRaffleModal()
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
            await interaction.response.send_message("There is no ongoing raffle! You need to start a new one.")
            return

        raffle_message_id = DB().get_raffle_message_id(interaction.guild.id)
        if raffle_message_id is None:
            await interaction.response.send_message("Oops! That raffle does not exist anymore.")
            return

        await RaffleCog._end_raffle_impl(interaction, raffle_message_id, num_winners)
        DB().close_raffle(interaction.guild.id, end_time=datetime.now())

    @staticmethod
    async def _end_raffle_impl(
        interaction: Interaction,
        raffle_message_id: int,
        num_winners: int,
    ) -> None:
        guild_id = interaction.guild.id
        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        if raffle_message is None:
            raise Exception("Oops! That raffle does not exist anymore.")

        # ineligible_winner_ids = DB().recent_winner_ids(guild_id)
        # entrants = set(u for u in entrant_list if u.id not in ineligible_winner_ids)

        raffle_entries = DB().get_raffle_entries(guild_id)
        entrants = [interaction.guild.get_member(e.user_id) for e in raffle_entries]

        if len(entrants) == 0:
            await interaction.response.send_message("No one eligible entered the raffle so there is no winner.")
            return

        winners = RaffleCog.choose_winners(guild_id, list(entrants), num_winners)
        winner_ids = [w.id for w in winners]

        if len(winners) == 1:
            await interaction.response.send_message(f"{winners[0].mention} has won the raffle!")
        else:
            await interaction.response.send_message(
                f"Raffle winners are: {', '.join(w.mention for w in winners)}!"
            )

        DB().record_win(guild_id, winner_ids)

    @staticmethod
    def choose_winners(
        guild_id: int, entrants: list[Member], num_winners: int
    ) -> list[Member]:
        """
        Every raffle entry starts with 100 "tickets". Certain roles will get extra tickets.

        Then we let random.choices work its magic.
        """
        if len(entrants) < num_winners:
            raise Exception("There are not enough entrants for that many winners.")

        # step 1. fetch all role modifiers
        role_modifiers = DB().get_role_modifiers(guild_id)

        # step 2. calculate tickets-per-entrant
        entrant_tickets = []
        for ent in entrants:
            # every entrant starts with 100 ticket + any ticket modifiers per role
            tickets = 100 + sum(role_modifiers.get(r.id, 0) for r in ent.roles)
            entrant_tickets.append(tickets)

        # step 3. using weighted probability, select a random winner
        winners = random.choices(entrants, weights=entrant_tickets, k=num_winners)

        return winners

    @staticmethod
    def get_tickets(guild_id: int, user: Member) -> int:
        """
        Calculate the number of tickers a specific user should have for a raffle entry.
        """
        # fetch all role modifiers for the guild
        role_modifiers = DB().get_role_modifiers(guild_id)

        # calculate tickets
        # every entrant starts with 100 ticket + any ticket modifiers per role
        return 100 + sum(role_modifiers.get(r.id, 0) for r in user.roles)


async def main():
    async with client:
        tree.add_command(RaffleCog(tree))
        await client.start(Config.CONFIG["Discord"]["Token"])

if __name__ == "__main__":
    asyncio.run(main())

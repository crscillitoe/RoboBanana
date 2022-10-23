from __future__ import annotations
import asyncio
import configparser
import logging
import discord
from datetime import datetime, timedelta
from discord import app_commands, ButtonStyle, Client, Embed, Intents, Interaction, Member, Message, TextStyle
from discord.ui import Button, TextInput, Modal, View
from enum import Enum
import numpy
import os
import random
from DB import DB

discord.utils.setup_logging(level=logging.INFO, root=False)

intents = Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

client = Client(intents=intents)
tree = app_commands.CommandTree(client)

config = configparser.ConfigParser()
config.read(os.environ.get("CONFIG_PATH"))

class RaffleType(Enum):
    Normal = "normal"   # Normal Raffle type. Most recent 6 winners are not eligible to win
    Anyone = "anyone"   # No restrictions. Anyone can win. But win is still recorded.
    New = "new"         # Only people who have never won a raffle are eligible

class RaffleView(View):
    def __init__(self, parent: RaffleEmbed, raffle_type: RaffleType, num_winners: int) -> None:
        super().__init__(timeout=None)

        self.parent = parent

        self.entrants: list[Member] = []
        self.winners: list[Member] = None
        self.raffle_type = raffle_type
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

    async def enter_raffle_onclick(self, interaction: Interaction):
        user = interaction.user
        if user in self.entrants:
            await interaction.response.send_message("You have already entered this raffle!", ephemeral=True)
            return

        self.entrants.append(user)
        self.parent.update_fields()

        raffle_message_id = DB.get().get_raffle_message_id(interaction.guild.id)
        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        await raffle_message.edit(embed=self.parent)

        await interaction.response.send_message("Raffle entered!", ephemeral=True)

    async def end_raffle_onclick(self, interaction: Interaction):
        if not DB.get().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message("This raffle is no longer active!")
            return

        raffle_message_id = DB.get().get_raffle_message_id(interaction.guild.id)
        if raffle_message_id is None:
            await interaction.response.send_message("Oops! That raffle does not exist anymore.")
            return

        self.enter_raffle_button.disabled = True
        self.end_raffle_button.disabled = True
        self.redo_raffle_button.disabled = False

        self.parent.end_time = int(datetime.now().timestamp())
        self.parent.update_fields()

        await RaffleCog._end_raffle_impl(interaction, raffle_message_id, self.raffle_type, self.num_winners, self.entrants)
        DB.get().close_raffle(interaction.guild.id)

        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        await raffle_message.edit(embed=self.parent, view=self)


    async def redo_raffle_onclick(self, interaction: Interaction):
        modal = RedoRaffleModal(raffle_message=interaction.message, entrants=self.entrants)
        await interaction.response.send_modal(modal)


def get_raffle_embed(
    description: str | None,
    raffle_type: RaffleType,
    num_winners: int,
    duration: int,
) -> tuple(Embed, View):
    """Generate a raffle embed for participants to interact with."""
    embed = RaffleEmbed(
        description=description,
        raffle_type=raffle_type,
        num_winners=num_winners,
        duration=duration,
    )
    return (embed, embed.buttons_view)

class RaffleEmbed(Embed):
    def __init__(self,
        description: str | None,
        raffle_type: RaffleType,
        num_winners: int,
        duration: int,
    ):
        super().__init__(
            title="VOD Review Raffle",
            description=description,
        )

        self.buttons_view = RaffleView(parent=self, raffle_type=raffle_type, num_winners=num_winners)

        self.end_time = int((datetime.now() + timedelta(seconds=duration)).timestamp())
        self.update_fields()

    def update_fields(self) -> None:
        self.clear_fields()
        self.add_field(name="Raffle End", value=f"<t:{self.end_time}:R>", inline=True)
        self.add_field(name="Total Entries", value=str(len(self.buttons_view.entrants)), inline=True)

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
        self.raffle_type = TextInput(
            label="Raffle Type (normal/anyone/new)",
            default="normal",
            placeholder="normal, anyone, or new",
            style=TextStyle.short,
            required=True,
            min_length=3,
            max_length=6,
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
        self.add_item(self.raffle_type)
        self.add_item(self.num_winners)
        self.add_item(self.description)

    async def on_submit(self, interaction: Interaction) -> None:
        # validate inputs
        try:
            raffle_type = RaffleType(self.raffle_type.value.lower())
        except ValueError:
            await interaction.response.send_message('Invalid raffle type.', ephemeral=True)
            return

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

        embed, view = get_raffle_embed(description=description, raffle_type=raffle_type, num_winners=num_winners, duration=duration)
        await interaction.response.send_message(embed=embed, view=view)
        raffle_message = await interaction.original_response()

        DB.get().create_raffle(interaction.guild.id, raffle_message.id)

class RedoRaffleModal(Modal, title="Redo Raffle"):
    def __init__(self, raffle_message: Message, entrants: list[Member]) -> None:
        super().__init__(timeout=None)

        self.raffle_message = raffle_message
        self.entrants = entrants

        self.raffle_type = TextInput(
            label="Raffle Type (normal/anyone/new)",
            default="normal",
            placeholder="normal, anyone, or new",
            style=TextStyle.short,
            required=True,
            min_length=3,
            max_length=6,
        )
        self.num_winners = TextInput(
            label="Number of Winners",
            default="1",
            placeholder="How many winners to draw (Must be an integer > 0)",
            style=TextStyle.short,
            required=True,
            min_length=1,
            max_length=2
        )

        self.add_item(self.raffle_type)
        self.add_item(self.num_winners)

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            raffle_type = RaffleType(self.raffle_type.value.lower())
        except ValueError:
            await interaction.response.send_message('Invalid raffle type.', ephemeral=True)
            return

        try:
            num_winners = int(self.num_winners.value)
        except ValueError:
            await interaction.response.send_message('Invalid number of winners.', ephemeral=True)
            return

        DB.get().clear_wins(interaction.guild.id, self.raffle_message.id)

        await RaffleCog._end_raffle_impl(interaction, self.raffle_message.id, raffle_type, num_winners, self.entrants)


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

        if DB.get().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message("There is already an ongoing raffle!")
            return

        modal = NewRaffleModal()
        await interaction.response.send_modal(modal)

    @app_commands.command(name="end")
    @app_commands.describe(raffle_type="Type of raffle (default = Normal)")
    @app_commands.checks.has_role("Mod")
    async def end(
        self,
        interaction: Interaction,
        raffle_type: RaffleType = RaffleType.Normal,
        num_winners: int = 1,
    ) -> None:
        """Closes an existing raffle and pick the winner(s)"""

        if not DB.get().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message("There is no ongoing raffle! You need to start a new one.")
            return

        raffle_message_id = DB.get().get_raffle_message_id(interaction.guild.id)
        if raffle_message_id is None:
            await interaction.response.send_message("Oops! That raffle does not exist anymore.")
            return

        await RaffleCog._end_raffle_impl(interaction, raffle_message_id, raffle_type, num_winners, [])
        DB.get().close_raffle(interaction.guild.id)

    @staticmethod
    async def _end_raffle_impl(
        interaction: Interaction,
        raffle_message_id: int,
        raffle_type: RaffleType,
        num_winners: int,
        entrant_list: list[Member],
    ) -> None:
        guild_id = interaction.guild.id
        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        if raffle_message is None:
            raise Exception("Oops! That raffle does not exist anymore.")

        match raffle_type:
            case RaffleType.Normal:
                recent_raffle_winner_ids = DB.get().recent_winner_ids(guild_id)
                past_week_winner_ids = DB.get().past_week_winner_ids(guild_id)
                ineligible_winner_ids = recent_raffle_winner_ids.union(past_week_winner_ids)
            case RaffleType.Anyone:
                ineligible_winner_ids = set()
            case RaffleType.New:
                ineligible_winner_ids = DB.get().all_winner_ids(guild_id)
            case _:
                raise Exception(f"Unimplemented raffle type: {raffle_type}")

        entrants = set(u for u in entrant_list if u.id not in ineligible_winner_ids)

        # Certain servers may only want you to be eligible for a raffle if you have
        # given role(s). These are checked as ORs meaning if you have at least one
        # of the configured roles you are eligible to win.
        eligible_role_ids = DB.get().eligible_role_ids(guild_id)
        if len(eligible_role_ids) > 0:
            for entrant in entrants.copy():
                if eligible_role_ids.intersection(RaffleCog._get_role_ids(entrant)) == set():
                    entrants.remove(entrant)

        if len(entrants) == 0:
            await interaction.response.send_message("No one eligible entered the raffle so there is no winner.")
            return

        if raffle_type == RaffleType.Normal:
            winners = RaffleCog._choose_winners_weighted(guild_id, list(entrants), num_winners)
        else:
            winners = RaffleCog._choose_winners_unweighted(list(entrants), num_winners)

        if raffle_type != RaffleType.Anyone:
            DB.get().record_win(guild_id, raffle_message_id, *winners)

        if len(winners) == 1:
            await interaction.response.send_message(f"{winners[0].mention} has won the raffle!")
        else:
            await interaction.response.send_message(
                f"Raffle winners are: {', '.join(map(lambda w: w.mention, winners))}!"
            )


    @staticmethod
    def _choose_winners_unweighted(
        entrants: list[Member], num_winners: int
    ) -> list[Member]:
        if len(entrants) < num_winners:
            raise Exception("There are not enough entrants for that many winners.")

        winners = []
        while num_winners > 0:
            winner = random.choice(entrants)
            winners.append(winner)
            entrants.remove(winner)
            num_winners -= 1

        return winners


    @staticmethod
    def _choose_winners_weighted(
        guild_id: int, entrants: list[Member], num_winners: int
    ) -> list[Member]:
        """
        Purpose of this algorithm is to choose winners in a way that actually lowers
        their chances the more raffles they've won in the past.
        Conceptually, can think of it as giving out more raffle "tickets" to those that have not won as often.

        Each raffle win lowers your relative odds of winning by 25%.
        So someone who has won once is 0.75x as likely to win as someone who has never won.
        Someone who's won twice is 0.5625x (0.75^2) as likely as someone who has never won.
        And so on.

        Here's how it works.

        We start by fetching the past wins of everyone in the guild.
        Then, of the current raffle entrants, we start with the person who's won the most times.
        Going from that win count -> 0 we figure out the ticket distribution factor for each bucket of win counts.
        Then we figure out how many tickets they should get for each bucket based on that distribution factor.
        That then gives us the relative probability array that gets fed into random.choice

        Here's an example.

        Say we have the following entrants:
        8 people who've won 0 times
        5 people who have won 1 time
        2 people who have won 2 times
        1 person who has won 4 times

        Highest win count is 4 wins so we start there.
        That bucket awards 1 ticket and then we calculate the fewer-win bucket tickets:
        4 wins -> 1 ticket
        3 wins -> 4/3 (~1.3) tickets
        2 wins -> 16/9 (~1.8) tickets
        1 win -> 64/27 (~2.4) tickets
        0 wins -> 256/81 (~3.16) tickets

        This way: 4 wins gets 0.75x as many tickets as 3 wins,
        3 wins gets 0.75x as many tickets as 2 wins, and so on.

        Total tickets given out is the sum of each bucket's tickets the number of entrants:
        8 entrants * 256/81 tickets
        + 5 * 64/27
        + 2 * 16/9
        + 0 * 4/3
        + 1 * 1
        = ~41.7 tickets

        Now, the p-list values should all sum up to 1. So we treat those tickets as
        portions of a "single ticket" and give out those portions.
        We do that by taking the reciprocal, so 1/41.7 = 0.0239857862

        0.0239857862 now is the chance of winning if you were given one "ticket".
        Then we divvy out those tickets according to the number awarded per win bucket.

        So then we end with:
        8 people get 256/81 * 0.0239857862 = 0.07580692922 "tickets"
        5 people get 64/27 * 0.0239857862 = 0.05685519692 tickets
        2 people get 16/9 * 0.0239857862 = 0.04264139769 tickets
        1 person gets 1 * 0.0239857862 = 0.0239857862 tickets

        As a check, if we add all those up, it should equal 1.
        0.07580692922 * 8 + 0.05685519692 * 5 + 0.04264139769 * 2 + 0.0239857862 = 0.9999999999

        So then for our p-list, our resultant structure is:
        [0.07580692922, 0.07580692922, 0.07580692922, ..., 0.04264139769, 0.04264139769, 0.0239857862]

        And we sort the corresponding entrants list by their win counts ascending so the two lists line up.
        [0-wins entrant, 0-wins entrant, 0-wins entrant, ..., 2-wins entrant, 2-wins entrant, 4-wins entrant]

        Then we let numpy.random.choice work its magic.
        """
        if len(entrants) < num_winners:
            raise Exception("There are not enough entrants for that many winners.")

        # Just to add even more randomness
        random.shuffle(entrants)
        random.shuffle(entrants)
        random.shuffle(entrants)

        past_winner_win_counts = DB.get().win_counts(guild_id)
        entrants = sorted(
            entrants, key=lambda entrant: past_winner_win_counts.get(entrant.id, 0)
        )

        total_win_counts = {}
        for entrant in entrants:
            entrant_past_wins = past_winner_win_counts.get(entrant.id, 0)
            if entrant_past_wins not in total_win_counts:
                total_win_counts[entrant_past_wins] = 1
            else:
                total_win_counts[entrant_past_wins] += 1

        tickets_per_win_bucket = {}
        highest_entrant_wins = max(total_win_counts.keys())
        for i in range(highest_entrant_wins, -1, -1):
            tickets_per_win_bucket[i] = (4 / 3) ** (highest_entrant_wins - i)

        total_tickets = 0
        for win, tickets in tickets_per_win_bucket.items():
            total_tickets += total_win_counts.get(win, 0) * tickets

        value_of_one_ticket = 1 / total_tickets
        for win, multiplier in tickets_per_win_bucket.copy().items():
            tickets_per_win_bucket[win] = multiplier * value_of_one_ticket

        p_list = []
        for win, tickets in reversed(tickets_per_win_bucket.items()):
            for i in range(0, total_win_counts.get(win, 0)):
                p_list.append(tickets)

        return numpy.random.choice(entrants, num_winners, replace=False, p=p_list)


    @staticmethod
    def _get_role_ids(member: Member) -> set[int]:
        return set(map(lambda role: role.id, member.roles))


async def main():
    async with client:
        tree.add_command(RaffleCog(tree))
        await client.start(config["Discord"]["Token"])

if __name__ == "__main__":
    asyncio.run(main())

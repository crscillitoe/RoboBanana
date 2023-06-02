from discord.ui import Modal, TextInput
from discord import TextStyle, Interaction
from datetime import datetime, timedelta
from db import DB, RaffleType
from .raffle_embed import RaffleEmbed
from .raffle_view import RaffleView


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
            default=(
                "Raffle time! Click below to enter. The winner(s) will be randomly"
                " chosen."
            ),
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

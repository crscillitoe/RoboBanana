from discord import Message, Interaction, TextStyle
from discord.ui import Modal, TextInput
from datetime import datetime
from controllers.raffle_controller import RaffleController
from db import DB


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

        await RaffleController._end_raffle_impl(
            interaction, self.raffle_message.id, num_winners
        )

        DB().close_raffle(interaction.guild.id, end_time=datetime.now())

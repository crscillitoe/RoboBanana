from discord import ButtonStyle, Interaction
from discord.ui import View, Button
from controllers.prediction_controller import PredictionController
from db import DB


class PayoutPredictionView(View):
    def __init__(self, option_one: str, option_two: str) -> None:
        super().__init__(timeout=None)

        self.option_one = option_one
        self.option_two = option_two

        self.option_one_button = Button(
            label=option_one,
            style=ButtonStyle.blurple,
            custom_id="payout_prediction_view:option_one_button",
        )
        self.option_one_button.callback = self.option_one_onclick
        self.add_item(self.option_one_button)

        self.option_two_button = Button(
            label=option_two,
            style=ButtonStyle.secondary,
            custom_id="payout_prediction_view:option_two_button",
        )
        self.option_two_button.callback = self.option_two_onclick
        self.add_item(self.option_two_button)

    async def option_one_onclick(self, interaction: Interaction):
        await PredictionController.payout_prediction(0, interaction)
        self.option_one_button.disabled = True
        self.option_two_button.disabled = True
        await interaction.message.edit(content="", view=self)

    async def option_two_onclick(self, interaction: Interaction):
        await PredictionController.payout_prediction(1, interaction)
        self.option_one_button.disabled = True
        self.option_two_button.disabled = True
        await interaction.message.edit(content="", view=self)

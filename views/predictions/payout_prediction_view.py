from discord import ButtonStyle, Interaction, Client
from discord.ui import View, Button
from controllers.predictions.payout_prediction_controller import (
    PayoutPredictionController,
)
from db import DB
from db.models import PredictionChoice


class PayoutPredictionView(View):
    def __init__(self, option_one: str, option_two: str, client: Client) -> None:
        super().__init__(timeout=None)

        self.option_one = option_one
        self.option_two = option_two
        self.client = client

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

        self.refund_button = Button(
            label="Refund Prediction",
            style=ButtonStyle.red,
            custom_id="payout_prediction_view:refund_button",
        )
        self.refund_button.callback = self.refund_onclick
        self.add_item(self.refund_button)

    async def option_one_onclick(self, interaction: Interaction):
        await PayoutPredictionController.payout_prediction(
            PredictionChoice.left, interaction, self.client
        )
        self.option_one_button.disabled = True
        self.option_two_button.disabled = True
        self.refund_button.disabled = True
        await interaction.message.edit(content="", view=self)

    async def option_two_onclick(self, interaction: Interaction):
        await PayoutPredictionController.payout_prediction(
            PredictionChoice.right, interaction, self.client
        )
        self.option_one_button.disabled = True
        self.option_two_button.disabled = True
        self.refund_button.disabled = True
        await interaction.message.edit(content="", view=self)

    async def refund_onclick(self, interaction: Interaction):
        await PayoutPredictionController.refund_prediction(interaction, self.client)
        self.option_one_button.disabled = True
        self.option_two_button.disabled = True
        self.refund_button.disabled = True
        await interaction.message.edit(content="", view=self)

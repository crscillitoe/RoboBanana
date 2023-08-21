from discord import Client, Interaction
from threading import Thread
from controllers.predictions.update_prediction_controller import (
    UpdatePredictionController,
)
from db.models import (
    PredictionChoice,
)
from db import DB


class PredictionEntryController:
    @staticmethod
    async def create_prediction_entry(
        channel_points: int,
        guess: PredictionChoice,
        interaction: Interaction,
        client: Client,
    ) -> bool:
        if not DB().accepting_prediction_entries(interaction.guild_id):
            return await interaction.response.send_message(
                "Predictions are currently closed!", ephemeral=True
            )

        if channel_points <= 0:
            return await interaction.response.send_message(
                "You must wager a positive number of points!", ephemeral=True
            )

        point_balance = DB().get_point_balance(interaction.user.id)
        if channel_points > point_balance:
            return await interaction.response.send_message(
                f"You can only wager up to {point_balance} points", ephemeral=True
            )

        result, _ = DB().withdraw_points(interaction.user.id, channel_points)
        if not result:
            return await interaction.response.send_message(
                "Unable to cast vote - please try again!", ephemeral=True
            )

        success = DB().create_prediction_entry(
            interaction.guild_id, interaction.user.id, channel_points, guess.value
        )
        if not success:
            await interaction.response.send_message(
                "Unable to cast vote", ephemeral=True
            )
            return False

        prediction_id = DB().get_ongoing_prediction_id(interaction.guild_id)

        channel_id = DB().get_prediction_channel_id(prediction_id)
        message_id = DB().get_prediction_message_id(prediction_id)

        # We'll use this prediction summary for the reply message
        prediction_summary = DB().get_prediction_summary(prediction_id)
        Thread(
            target=UpdatePredictionController.publish_update, args=(prediction_summary,)
        ).start()

        chosen_option = (
            prediction_summary.option_one
            if guess == PredictionChoice.left
            else prediction_summary.option_two
        )
        prediction_message = await client.get_channel(channel_id).fetch_message(
            message_id
        )
        await prediction_message.reply(
            f"{interaction.user.mention} bet {channel_points} hooj bucks on"
            f" {chosen_option}"
        )
        return True

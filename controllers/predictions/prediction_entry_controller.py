from discord import Client, Forbidden, Interaction, Member
from threading import Thread
from config import YAMLConfig as Config
from controllers.point_history_controller import PointHistoryController
from controllers.predictions.nickname_prediction_controller import (
    NicknamePredictionController,
)
from controllers.predictions.update_prediction_controller import (
    UpdatePredictionController,
)
from db.models import (
    PredictionChoice,
)
from db import DB
from models.transaction import Transaction
import logging

LOG = logging.getLogger(__name__)


class PredictionEntryController:
    @staticmethod
    async def create_prediction_entry(
        channel_points: int,
        guess: PredictionChoice,
        interaction: Interaction,
        client: Client,
    ) -> bool:
        if not DB().accepting_prediction_entries(interaction.guild_id):
            return await interaction.followup.send(
                "Predictions are currently closed!", ephemeral=True
            )

        if channel_points <= 0:
            return await interaction.followup.send(
                "You must wager a positive number of points!", ephemeral=True
            )

        point_balance = DB().get_point_balance(interaction.user.id)
        if channel_points > point_balance:
            return await interaction.followup.send(
                f"You can only wager up to {point_balance} points", ephemeral=True
            )

        result, new_balance = DB().withdraw_points(interaction.user.id, channel_points)
        if not result:
            return await interaction.followup.send(
                "Unable to cast vote - please try again!", ephemeral=True
            )

        PointHistoryController.record_transaction(
            Transaction(
                interaction.user.id,
                -channel_points,
                point_balance,
                new_balance,
                f"Prediction Entry ({guess.name})",
            )
        )

        success = DB().create_prediction_entry(
            interaction.guild_id, interaction.user.id, channel_points, guess.value
        )
        if not success:
            await interaction.followup.send("Unable to cast vote", ephemeral=True)
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

        append = ""
        if prediction_summary.set_nickname == True:
            if len(f"{chosen_option} {interaction.user.display_name}") > 32:
                append = f"\nPlease manually set your nickname using the `/nick` command to include {chosen_option} at the start of your name."
            elif (
                interaction.user.display_name.split(" ")[0].lower()
                == chosen_option.lower()
            ):
                pass
            else:
                acc = NicknamePredictionController.get_accumulator(
                    prediction_id, interaction.guild
                )
                queue_size = acc.add(interaction.user.id, chosen_option)

                if queue_size == -1:  # No more space left in the queue
                    append = f"\nPlease manually set your nickname using the `/nick` command to include {chosen_option} at the start of your name."
                else:
                    append = f"\nYour nickname will automatically be set to `{chosen_option} {interaction.user.display_name}` in approximately {queue_size} seconds."
                    append += f"\nTo manually include {chosen_option} at the start of your nickname quicker, use the `/nick` command."

        prediction_message = await client.get_channel(channel_id).fetch_message(
            message_id
        )

        await prediction_message.reply(
            f"{interaction.user.mention} bet {channel_points} hooj bucks on"
            f" {chosen_option}"
        )

        await interaction.followup.send(
            f"Vote cast with {channel_points} points!{append}", ephemeral=True
        )

        return True

from discord import Client, Forbidden, Interaction, Member
from threading import Thread
from controllers.point_history_controller import PointHistoryController
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

        result, new_balance = DB().withdraw_points(interaction.user.id, channel_points)
        if not result:
            return await interaction.response.send_message(
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

        if prediction_summary.set_nickname == True:
            member = interaction.user
            if isinstance(
                member, Member
            ):  # Don't proceed if we somehow get a regular User
                old_name = member.display_name
                split = old_name.split(" ")
                if (
                    split[0].lower() != chosen_option.lower()
                    and (len(old_name) + len(chosen_option) + 1) <= 32
                ):  # Only proceed if the user doesn't have the tag already and the tag would fit
                    try:
                        await member.edit(nick=f"{chosen_option} {old_name}")
                    except (
                        Forbidden
                    ):  # This should only ever happen if we try to edit the Guild Owner
                        LOG.error(
                            f"[PREDICTION] Couldn't set nickname of user {member.id}. We are forbidden from editing the member."
                        )
                    except Exception as e:
                        LOG.error(
                            f"[PREDICTION] Couldn't set nickname of user {member.id}. {e}"
                        )

        prediction_message = await client.get_channel(channel_id).fetch_message(
            message_id
        )
        await prediction_message.reply(
            f"{interaction.user.mention} bet {channel_points} hooj bucks on"
            f" {chosen_option}"
        )
        return True

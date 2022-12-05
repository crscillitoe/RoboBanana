from datetime import datetime, timezone
from discord import Interaction, Client
from db import DB
from db.models import PredictionEntry, PredictionSummary
from threading import Thread
from config import Config
import logging
import requests

PUBLISH_URL = "http://localhost:3000/publish-prediction"
AUTH_TOKEN = Config.CONFIG["Server"]["AuthToken"]

LOG = logging.getLogger(__name__)


class PredictionController:
    @staticmethod
    async def payout_prediction(option: int, interaction: Interaction, client: Client):
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

        publish_prediction_end_summary(interaction.guild_id)

        payout_message = f"Payout complete! {total_points} points distributed."
        await reply_to_initial_message(interaction.guild_id, client, payout_message)

        DB().complete_prediction(interaction.guild_id)
        await interaction.response.send_message(payout_message, ephemeral=True)

    @staticmethod
    async def refund_prediction(interaction: Interaction, client: Client):
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

        publish_prediction_end_summary(interaction.guild_id)

        refund_message = "Prediction has been refunded!"
        await reply_to_initial_message(interaction.guild_id, client, refund_message)

        DB().complete_prediction(interaction.guild_id)
        await interaction.response.send_message(refund_message, ephemeral=True)

    @staticmethod
    async def create_prediction_entry(
        channel_points: int,
        point_balance: int,
        guess: int,
        interaction: Interaction,
        client: Client,
    ):
        if channel_points > point_balance:
            return await interaction.response.send_message(
                f"You can only wager up to {point_balance} points", ephemeral=True
            )

        result, _ = DB().withdraw_points(interaction.user.id, channel_points)
        if not result:
            return await interaction.response.send_message(
                "Unable to cast vote - please try again!", ephemeral=True
            )

        DB().create_prediction_entry(
            interaction.guild_id, interaction.user.id, channel_points, guess
        )

        channel_id = DB().get_prediction_channel_id(interaction.guild_id)
        message_id = DB().get_prediction_message_id(interaction.guild_id)

        # We'll use this prediction summary for the reply message
        prediction_summary = DB().get_prediction_summary(interaction.guild_id)
        Thread(target=publish_update, args=(prediction_summary,)).start()

        chosen_option = (
            prediction_summary.option_one
            if guess == 0
            else prediction_summary.option_two
        )
        prediction_message = await client.get_channel(channel_id).fetch_message(
            message_id
        )
        await prediction_message.reply(
            f"{interaction.user.mention} bet {channel_points} hooj bucks on {chosen_option}"
        )

    @staticmethod
    async def create_prediction(
        guild_id: int,
        channel_id: int,
        message_id: str,
        description: str,
        option_one: str,
        option_two: str,
        end_time: datetime,
    ):
        DB().create_prediction(
            guild_id,
            channel_id,
            message_id,
            description,
            option_one,
            option_two,
            end_time,
        )
        publish_prediction_summary(guild_id)

    @staticmethod
    async def close_prediction(guild_id: int):
        DB().close_prediction(guild_id)
        publish_prediction_summary(guild_id)


def publish_update(prediction_summary: PredictionSummary):
    payload = {
        "description": prediction_summary.description,
        "optionOne": prediction_summary.option_one,
        "optionTwo": prediction_summary.option_two,
        "optionOnePoints": prediction_summary.option_one_points,
        "optionTwoPoints": prediction_summary.option_two_points,
        "endTime": prediction_summary.end_time.astimezone(timezone.utc).isoformat(),
        "acceptingEntries": prediction_summary.accepting_entries,
        "ended": prediction_summary.ended,
    }
    response = requests.post(
        url=PUBLISH_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )
    if response.status_code != 200:
        LOG.error(f"Failed to publish updated prediction summary: {response.text}")


async def reply_to_initial_message(guild_id: int, client: Client, message: str):
    prediction_message_id = DB().get_prediction_message_id(guild_id)
    prediction_channel_id = DB().get_prediction_channel_id(guild_id)
    prediction_message = await client.get_channel(prediction_channel_id).fetch_message(
        prediction_message_id
    )
    await prediction_message.reply(message)


def publish_prediction_summary(guild_id: int):
    prediction_summary = DB().get_prediction_summary(guild_id)
    Thread(target=publish_update, args=(prediction_summary,)).start()


def publish_prediction_end_summary(guild_id: int):
    prediction_summary = DB().get_prediction_summary(guild_id)
    prediction_summary.ended = True
    Thread(target=publish_update, args=(prediction_summary,)).start()

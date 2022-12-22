from datetime import datetime, timezone
from typing import Generator, Optional, Tuple
from discord import Interaction, Client
from db import DB
from db.models import (
    PredictionChoice,
    PredictionOutcome,
    PredictionEntry,
    PredictionSummary,
)
from threading import Thread
from config import Config
import logging
import requests

PUBLISH_URL = "http://localhost:3000/publish-prediction"
AUTH_TOKEN = Config.CONFIG["Server"]["AuthToken"]

LOG = logging.getLogger(__name__)

REFUND_PREDICTION_CHOICE = -1


class ReturnableGenerator:
    def __init__(self, gen):
        self.gen = gen

    def __iter__(self):
        self.return_value = yield from self.gen


class PredictionController:
    @staticmethod
    def get_winning_pot(winning_option: int, option_one: int, option_two: int):
        if winning_option == PredictionChoice.pink.value:
            return option_one
        elif winning_option == PredictionChoice.blue.value:
            return option_two
        else:
            raise ValueError(f"Invalid PredictionChoice provided: {winning_option}")

    @staticmethod
    def calculate_payout(entry: PredictionEntry, winning_pot: int, total_points: int):
        pot_percentage = entry.channel_points / winning_pot
        return round(total_points * pot_percentage)

    @staticmethod
    def get_payout_for_option(
        option: int, prediction_id: int
    ) -> Generator[Tuple[int, int], None, int]:
        option_one, option_two = DB().get_prediction_point_counts(prediction_id)
        total_points = option_one + option_two
        winning_pot = PredictionController.get_winning_pot(
            option, option_one, option_two
        )
        entries: list[PredictionEntry] = DB().get_prediction_entries_for_guess(
            prediction_id, option
        )

        for entry in entries:
            payout = PredictionController.calculate_payout(
                entry, winning_pot, total_points
            )
            yield entry.user_id, payout
        return total_points

    @staticmethod
    async def payout_prediction(
        option: PredictionChoice, interaction: Interaction, client: Client
    ):
        if not DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "No ongoing prediction!", ephemeral=True
            )

        if DB().accepting_prediction_entries(interaction.guild_id):
            return await interaction.response.send_message(
                "Please close prediction from entries before paying out!",
                ephemeral=True,
            )

        prediction_id = DB().get_ongoing_prediction_id(interaction.guild_id)
        payout_generator = ReturnableGenerator(
            PredictionController.get_payout_for_option(option.value, prediction_id)
        )

        for user_id, payout in payout_generator:
            DB().deposit_points(user_id, payout)

        total_points = payout_generator.return_value

        prediction_summary = DB().get_prediction_summary(prediction_id)
        publish_prediction_end_summary(prediction_id, prediction_summary)

        paid_option = (
            prediction_summary.option_one
            if option == PredictionChoice.pink
            else prediction_summary.option_two
        )

        payout_message = (
            f"Payout complete! {total_points} points distributed to {paid_option}."
        )
        await reply_to_initial_message(prediction_id, client, payout_message)

        DB().complete_prediction(interaction.guild_id, option.value)
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

        prediction_id = DB().get_ongoing_prediction_id(interaction.guild_id)

        option_one_entries = DB().get_prediction_entries_for_guess(prediction_id, 0)

        option_two_entries = DB().get_prediction_entries_for_guess(prediction_id, 1)

        entries = option_one_entries + option_two_entries
        for entry in entries:
            DB().deposit_points(entry.user_id, entry.channel_points)

        publish_prediction_end_summary(prediction_id)

        refund_message = "Prediction has been refunded!"
        await reply_to_initial_message(prediction_id, client, refund_message)

        DB().complete_prediction(interaction.guild_id, PredictionOutcome.refund.value)
        await interaction.response.send_message(refund_message, ephemeral=True)

    @staticmethod
    async def redo_payout(
        option: PredictionOutcome, interaction: Interaction, client: Client
    ):
        prediction = DB().get_last_prediction(interaction.guild_id)
        if prediction.winning_option is None:
            return await interaction.response.send_message(
                "Previous prediction has not yet been completed!", ephemeral=True
            )

        if prediction.winning_option == option.value:
            return await interaction.response.send_message(
                f"Prediction outcome is already {option.name}", ephemeral=True
            )

        if prediction.winning_option != PredictionOutcome.refund.value:
            # Withdraw points from previous winners
            payout_generator = PredictionController.get_payout_for_option(
                prediction.winning_option, interaction.guild_id, prediction.id
            )

            for user_id, payout in payout_generator:
                DB().withdraw_points(user_id, payout)

        if option != PredictionOutcome.refund:
            payout_generator = ReturnableGenerator(
                PredictionController.get_payout_for_option(
                    option.value, interaction.guild_id, prediction.id
                )
            )

            for user_id, payout in payout_generator:
                DB().deposit_points(user_id, payout)

            total_points = payout_generator.return_value

            payout_message = (
                f"Payout complete! {total_points} points distributed to {option.name}."
            )
            # await reply_to_initial_message(interaction.guild_id, client, payout_message)
            return await interaction.response.send_message(
                payout_message, ephemeral=True
            )

    @staticmethod
    async def create_prediction_entry(
        channel_points: int,
        guess: PredictionChoice,
        interaction: Interaction,
        client: Client,
    ) -> bool:
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
        Thread(target=publish_update, args=(prediction_summary,)).start()

        chosen_option = (
            prediction_summary.option_one
            if guess == PredictionChoice.pink
            else prediction_summary.option_two
        )
        prediction_message = await client.get_channel(channel_id).fetch_message(
            message_id
        )
        await prediction_message.reply(
            f"{interaction.user.mention} bet {channel_points} hooj bucks on {chosen_option}"
        )
        return True

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
        prediction_id = DB().get_ongoing_prediction_id(guild_id)
        publish_prediction_summary(prediction_id)

    @staticmethod
    async def close_prediction(guild_id: int):
        DB().close_prediction(guild_id)
        prediction_id = DB().get_ongoing_prediction_id(guild_id)
        publish_prediction_summary(prediction_id)


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


async def reply_to_initial_message(prediction_id: int, client: Client, message: str):
    prediction_message_id = DB().get_prediction_message_id(prediction_id)
    prediction_channel_id = DB().get_prediction_channel_id(prediction_id)
    prediction_message = await client.get_channel(prediction_channel_id).fetch_message(
        prediction_message_id
    )
    await prediction_message.reply(message)


def publish_prediction_summary(prediction_id: int):
    prediction_summary = DB().get_prediction_summary(prediction_id)
    Thread(target=publish_update, args=(prediction_summary,)).start()


def publish_prediction_end_summary(
    prediction_id: int, prediction_summary: Optional[PredictionSummary] = None
):
    if prediction_summary is None:
        prediction_summary = DB().get_prediction_summary(prediction_id)
    prediction_summary.ended = True
    Thread(target=publish_update, args=(prediction_summary,)).start()

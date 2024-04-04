from asyncio import Lock
import sys
from typing import Generator, Tuple

from discord import Client, Interaction
from controllers.point_history_controller import PointHistoryController
from controllers.predictions.nickname_prediction_controller import (
    NicknamePredictionController,
)
from controllers.predictions.update_prediction_controller import (
    UpdatePredictionController,
)
from db.models import (
    Prediction,
    PredictionChoice,
    PredictionOutcome,
    PredictionEntry,
    PredictionSummary,
)
from db import DB
import logging

from models.transaction import Transaction

LOG = logging.getLogger(__name__)
PREDICTION_LOCK = Lock()


class ReturnableGenerator:
    def __init__(self, gen):
        self.gen = gen

    def __iter__(self):
        self.return_value = yield from self.gen


class PayoutPredictionController:
    @staticmethod
    def get_winning_pot(winning_option: int, option_one: int, option_two: int):
        if winning_option == PredictionChoice.left.value:
            return option_one
        elif winning_option == PredictionChoice.right.value:
            return option_two
        else:
            raise ValueError(f"Invalid PredictionChoice provided: {winning_option}")

    @staticmethod
    def calculate_payout(entry: PredictionEntry, winning_pot: int, total_points: int):
        pot_percentage = entry.channel_points / winning_pot
        return round(total_points * pot_percentage)

    @staticmethod
    def get_entries_for_prediction(
        prediction_id: int,
    ) -> Generator[PredictionEntry, None, int]:
        option_one_entries = DB().get_prediction_entries_for_guess(prediction_id, 0)
        option_two_entries = DB().get_prediction_entries_for_guess(prediction_id, 1)
        entries = option_one_entries + option_two_entries
        total_points = 0
        for entry in entries:
            total_points += entry.channel_points
            yield entry
        return total_points

    @staticmethod
    def get_payout_for_option(
        option: int, prediction_id: int
    ) -> Generator[Tuple[int, int], None, int]:
        option_one, option_two = DB().get_prediction_point_counts(prediction_id)
        total_points = option_one + option_two
        winning_pot = PayoutPredictionController.get_winning_pot(
            option, option_one, option_two
        )
        entries: list[PredictionEntry] = DB().get_prediction_entries_for_guess(
            prediction_id, option
        )

        for entry in entries:
            payout = PayoutPredictionController.calculate_payout(
                entry, winning_pot, total_points
            )
            yield entry.user_id, payout
        return total_points

    @staticmethod
    async def _perform_payout(
        prediction_id: int,
        option: PredictionChoice,
        client: Client,
        guild_id: int,
    ):
        payout_generator = ReturnableGenerator(
            PayoutPredictionController.get_payout_for_option(
                option.value, prediction_id
            )
        )

        for user_id, payout in payout_generator:
            success, new_balance = DB().deposit_points(user_id, payout)
            if not success:
                LOG.warn(f"Failed to give points to {user_id}")
                continue
            PointHistoryController.record_transaction(
                Transaction(
                    user_id,
                    payout,
                    new_balance - payout,
                    new_balance,
                    f"Prediction Payout ({option.name})",
                )
            )

        total_points = payout_generator.return_value

        prediction_summary = DB().get_prediction_summary(prediction_id)
        UpdatePredictionController.publish_prediction_end_summary(
            prediction_id, prediction_summary
        )

        paid_option = (
            prediction_summary.option_one
            if option == PredictionChoice.left
            else prediction_summary.option_two
        )

        winning = 0
        losing = 0
        if option == PredictionChoice.left:
            winning = prediction_summary.option_one_points
            losing = prediction_summary.option_two_points
        else:
            winning = prediction_summary.option_two_points
            losing = prediction_summary.option_one_points

        winning_odds = calculate_multiplier(winning, losing)
        payout_message = f"Payout complete! {total_points} points distributed to {paid_option}. (Multiplier of {winning_odds}x)"
        await reply_to_initial_message(prediction_id, client, payout_message)

        if prediction_summary.set_nickname == True:
            guild = client.get_guild(guild_id)
            acc = NicknamePredictionController.get_accumulator(prediction_id, guild)
            acc.process_reset.start()
            payout_message = payout_message + "\nNickname reset in progress."

        return payout_message

    @staticmethod
    async def payout_prediction_for_guild(
        option: PredictionChoice, guild_id: int, client: Client
    ):
        await PREDICTION_LOCK.acquire()
        try:
            if not DB().has_ongoing_prediction(guild_id):
                return False, "No ongoing prediction!"

            if DB().accepting_prediction_entries(guild_id):
                return False, "Please close prediction from entries before paying out!"

            prediction_id = DB().get_ongoing_prediction_id(guild_id)
            payout_message = await PayoutPredictionController._perform_payout(
                prediction_id, option, client, guild_id
            )

            DB().complete_prediction(guild_id, option.value)
            return True, payout_message
        except:
            return False, "Failed to payout prediction!"
        finally:
            PREDICTION_LOCK.release()

    @staticmethod
    async def payout_prediction(
        option: PredictionChoice, interaction: Interaction, client: Client
    ):
        _, message = await PayoutPredictionController.payout_prediction_for_guild(
            option, interaction.guild_id, client
        )
        return await interaction.response.send_message(message, ephemeral=True)

    @staticmethod
    async def _perform_refund(prediction_id: int, client: Client, guild_id: int):
        for entry in PayoutPredictionController.get_entries_for_prediction(
            prediction_id
        ):
            result, new_balance = DB().deposit_points(
                entry.user_id, entry.channel_points
            )
            if not result:
                LOG.warn(f"Failed to return points to {entry.user_id}")
                continue
            PointHistoryController.record_transaction(
                Transaction(
                    entry.user_id,
                    entry.channel_points,
                    new_balance - entry.channel_points,
                    new_balance,
                    "Prediction Refund",
                )
            )

        UpdatePredictionController.publish_prediction_end_summary(prediction_id)

        refund_message = "Prediction has been refunded!"
        await reply_to_initial_message(prediction_id, client, refund_message)

        prediction_summary = DB().get_prediction_summary(prediction_id)

        if prediction_summary.set_nickname == True:
            guild = client.get_guild(guild_id)
            acc = NicknamePredictionController.get_accumulator(prediction_id, guild)
            acc.process_reset.start()
            refund_message = refund_message + "\nNicknames reset in progress."

        return refund_message

    @staticmethod
    async def refund_prediction_for_guild(guild_id: int, client: Client):
        await PREDICTION_LOCK.acquire()
        try:
            if not DB().has_ongoing_prediction(guild_id):
                return False, "No ongoing prediction!"

            if DB().accepting_prediction_entries(guild_id):
                return False, "Please close prediction from entries before refunding!"

            prediction_id = DB().get_ongoing_prediction_id(guild_id)
            refund_message = await PayoutPredictionController._perform_refund(
                prediction_id, client, guild_id
            )

            DB().complete_prediction(guild_id, PredictionOutcome.refund.value)
            return True, refund_message
        except:
            return False, "Failed to refund prediction!"
        finally:
            PREDICTION_LOCK.release()

    @staticmethod
    async def refund_prediction(interaction: Interaction, client: Client):
        _, message = await PayoutPredictionController.refund_prediction_for_guild(
            interaction.guild_id, client
        )
        return await interaction.response.send_message(message, ephemeral=True)

    @staticmethod
    def reset_points_from_payout(prediction: Prediction):
        """
        Resets points to the state they were in immediately prior to payout.
        This means that everyone's balance will return to what it was immediately
        after entering into the prediction.
        """
        if prediction.winning_option != PredictionOutcome.refund.value:
            # Withdraw points from previous winners
            payout_generator = PayoutPredictionController.get_payout_for_option(
                prediction.winning_option, prediction.id
            )

            for user_id, payout in payout_generator:
                DB().withdraw_points(user_id, payout)
        else:
            entry_generator = PayoutPredictionController.get_entries_for_prediction(
                prediction.id
            )
            for entry in entry_generator:
                DB().withdraw_points(entry.user_id, entry.channel_points)

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

        PayoutPredictionController.reset_points_from_payout(prediction)

        reply_message = ""
        if option != PredictionOutcome.refund:
            payout_option = (
                PredictionChoice.left
                if option == PredictionOutcome.left
                else PredictionChoice.right
            )
            reply_message = await PayoutPredictionController._perform_payout(
                prediction.id, payout_option, interaction, client
            )
        else:
            reply_message = await PayoutPredictionController._perform_refund(
                prediction.id, client
            )

        DB().set_prediction_outcome(prediction.id, option.value)
        await interaction.response.send_message(reply_message, ephemeral=True)

    @staticmethod
    async def _reset_prediction_nicknames(
        client: Client,
        prediction_id: int,
        prediction_summary: PredictionSummary,
        guild_id: int,
    ):
        guild = client.get_guild(guild_id)
        if not guild:
            LOG.error(f"Couldn't find guild {guild_id}, skipping nickname reset")
            return

        opt_one = prediction_summary.option_one
        opt_two = prediction_summary.option_two

        for entry in PayoutPredictionController.get_entries_for_prediction(
            prediction_id
        ):
            member = guild.get_member(entry.user_id)
            member_name = member.display_name
            split_name = member_name.split(" ")

            if split_name[0].lower() == opt_one.lower():
                member_name = member_name.replace(f"{opt_one} ", "", 1)
            elif split_name[0].lower() == opt_two.lower():
                member_name = member_name.replace(f"{opt_two} ", "", 1)
            else:
                continue

            await member.edit(nick=member_name)


async def reply_to_initial_message(prediction_id: int, client: Client, message: str):
    prediction_message_id = DB().get_prediction_message_id(prediction_id)
    prediction_channel_id = DB().get_prediction_channel_id(prediction_id)
    prediction_message = await client.get_channel(prediction_channel_id).fetch_message(
        prediction_message_id
    )
    await prediction_message.reply(message)


def calculate_multiplier(winning_points: int, losing_points: int):
    if winning_points == 0:
        return 1
    multiplier = 1 + (losing_points / winning_points)
    return round((multiplier + sys.float_info.epsilon) * 100) / 100

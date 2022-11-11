from discord import Interaction
from db import DB
from db.models import PredictionEntry


class PredictionController:
    @staticmethod
    async def payout_prediction(option: int, interaction: Interaction):
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

        DB().complete_prediction(interaction.guild_id)
        await interaction.response.send_message(
            f"Payout complete! {total_points} distributed.", ephemeral=True
        )

    @staticmethod
    async def refund_prediction(interaction: Interaction):
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

        DB().complete_prediction(interaction.guild_id)
        await interaction.response.send_message(
            "Prediction has been refunded!", ephemeral=True
        )

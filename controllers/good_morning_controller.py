from discord import Interaction
from db import DB
from config import Config

STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
GOOD_MORNING_EXPLANATION = "What's this message? <#1064317660084584619>"


class GoodMorningController:
    def get_good_morning_explanation():
        return GOOD_MORNING_EXPLANATION

    async def get_morning_points(interaction: Interaction):
        points = DB().get_morning_points(interaction.user.id)
        await interaction.response.send_message(
            f"Your current weekly count is {points}!", ephemeral=True
        )

    async def accrue_good_morning(interaction: Interaction):
        """Accrue good morning message point

        Args:
            message (Message): "good morning" stream chat message
        """
        if interaction.channel.id != STREAM_CHAT_ID:
            return await interaction.response.send_message(
                f"You can only say good morning in <#{STREAM_CHAT_ID}>!", ephemeral=True
            )

        accrued = DB().accrue_morning_points(interaction.user.id)
        if not accrued:
            return await interaction.response.send_message(
                "You've already said good morning today!", ephemeral=True
            )

        points = DB().get_morning_points(interaction.user.id)
        await interaction.response.send_message(
            (
                f"Good morning {interaction.user.mention}! "
                f"Your current weekly count is {points}!\n\n"
                f"{GOOD_MORNING_EXPLANATION}"
            )
        )

from discord import Colour, Embed, Interaction, User
from config import Config
from db import DB
import logging

HOURS_PER_REVIEW = int(Config.CONFIG["VODApproval"]["HoursPerReview"])
LOG = logging.getLogger(__name__)


class VODReviewBankController:
    @staticmethod
    async def increment_balance(user: User, interaction: Interaction):
        """Increment balance for one VOD review being performed

        Args:
            user (User): Discord User to increment balance for
            interaction (Interaction): Discord Command Interaction
        """
        await VODReviewBankController.add_balance(user, HOURS_PER_REVIEW, interaction)

    @staticmethod
    async def add_balance(user: User, amount: int, interaction: Interaction):
        new_balance = DB().add_vod_review_balance(user.id, amount)
        reply_content = f"Added {amount}h to {user.mention} VOD review balance. New balance: {new_balance}h"
        embed = Embed(
            title="VOD Bank Balance",
            description=reply_content,
            color=Colour.green(),
        )
        if interaction.response.is_done():
            return await interaction.followup.send(embed=embed, ephemeral=True)

        return await interaction.response.send_message(embed=embed, ephemeral=True)

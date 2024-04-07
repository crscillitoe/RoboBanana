from datetime import timedelta
from typing import Optional
from discord import Color, Colour, Embed, Interaction, User
from config import YAMLConfig as Config
from controllers.temprole_controller import TempRoleController
from db import DB
from pytimeparse.timeparse import timeparse
import logging

from util.discord_utils import DiscordUtils

LOG = logging.getLogger(__name__)
HOURS_PER_REVIEW = Config.CONFIG["Discord"]["VODReview"]["RewardHoursPerReview"]
GIFTED_T3_ROLE_ID = Config.CONFIG["Discord"]["Subscribers"]["GiftedTier3Role"]
SECONDS_IN_HOUR = 3600
# these are hardcoded until raze to radiant is over, or config file changes are allowed
# for testing on own setup, these need to be changed to your appropriate IDs
# TEMPROLE_AUDIT_CHANNEL should be 1225769539267199026 when committing and refers to the temprole-logs channel
TEMPROLE_AUDIT_CHANNEL = 1225769539267199026
COLOR_FAIL = Colour.red()
COLOR_SUCCESS = Colour.green()


class VODReviewBankController:
    @staticmethod
    async def get_balance(user: User, interaction: Interaction):
        balance = DB().get_vod_review_balance(user.id)
        if balance is None:
            balance = 0

        return await interaction.response.send_message(
            f"{user.mention} has {balance}h of VOD Review Credit", ephemeral=True
        )

    @staticmethod
    async def redeem_gifted_t3(
        user: User, duration: Optional[str], interaction: Interaction
    ):
        balance = DB().get_vod_review_balance(interaction.user.id)
        if balance is None or balance < 1:
            return await interaction.response.send_message(
                "Insufficient balance to redeem Gifted T3", ephemeral=True
            )

        if duration is None:
            duration = f"{balance}h"

        # Check to make sure user balance is enough
        duration_timedelta = timedelta(seconds=timeparse(duration))
        balance_timedelta = timedelta(hours=balance)

        if duration_timedelta > balance_timedelta:
            return await interaction.response.send_message(
                f"Insufficient balance for requested duration. Balance: {balance}h",
                ephemeral=True,
            )

        role = interaction.guild.get_role(GIFTED_T3_ROLE_ID)
        audit_channel = interaction.guild.get_channel(TEMPROLE_AUDIT_CHANNEL)
        audit_failed_message = (
            f"Tried to extend {role.name} for {user.mention} \n\n**System message:** "
        )
        if role is None:
            await DiscordUtils.audit(
                interaction,
                user,
                audit_failed_message + message,
                audit_channel,
                COLOR_FAIL,
            )
            return await interaction.response.send_message(
                f"Cannot find Gifted T3 role - check bot config!", ephemeral=True
            )
        success, message = await TempRoleController.extend_role(user, role, duration)
        if not success:
            embed = Embed(
                title="Failed to extend Gifted T3",
                description=message,
                color=Color.red(),
            )
            await DiscordUtils.audit(
                interaction,
                user,
                audit_failed_message + message,
                audit_channel,
                COLOR_FAIL,
            )
            return await DiscordUtils.reply(interaction, embed=embed)
        embed = Embed(
            title="Successfully extended Gifted T3",
            description=message,
            color=Color.green(),
        )
        await DiscordUtils.audit(
            interaction, user, message, audit_channel, COLOR_SUCCESS
        )
        await DiscordUtils.reply(interaction, embed=embed)

        duration_hours = duration_timedelta.total_seconds() / SECONDS_IN_HOUR
        DB().add_vod_review_balance(interaction.user.id, -duration_hours)

    @staticmethod
    async def increment_balance(user: User, interaction: Interaction):
        """Increment balance for one VOD review being performed

        Args:
            user (User): Discord User to increment balance for
            interaction (Interaction): Discord Command Interaction
        """
        await VODReviewBankController.add_balance(
            user, f"{HOURS_PER_REVIEW}h", interaction
        )

    @staticmethod
    async def add_balance(user: User, duration: str, interaction: Interaction):
        amount = (
            timedelta(seconds=timeparse(duration)).total_seconds() / SECONDS_IN_HOUR
        )
        new_balance = DB().add_vod_review_balance(user.id, amount)
        reply_content = (
            f"Added {amount}h to {user.mention} VOD review balance. New balance:"
            f" {new_balance}h"
        )
        embed = Embed(
            title="VOD Bank Balance",
            description=reply_content,
            color=Colour.green(),
        )
        return await DiscordUtils.reply(interaction, embed=embed, ephemeral=True)

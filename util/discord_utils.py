from discord import Interaction, TextChannel, Embed
import logging

LOG = logging.getLogger(__name__)


class DiscordUtils:
    @staticmethod
    async def reply(interaction: Interaction, *args, **kwargs):
        """Reply to an interaction regardless of if its been previously responded to"""
        if interaction.response.is_done():
            return await interaction.followup.send(*args, **kwargs)
        return await interaction.response.send_message(*args, **kwargs)

    @staticmethod
    async def audit(interaction: Interaction, message, channel: TextChannel, color):
        """Audit interaction in specified audit channel"""
        if channel is None:
            return LOG.error("Audit channel is not initialised")
        user = interaction.user.name
        userID = interaction.user.id
        embed = Embed(
            title=f"{user} (ID {userID})",
            description=message,
            color=color,
        )

        await channel.send(embed=embed)

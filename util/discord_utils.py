from discord import Interaction, TextChannel, Embed, User
import logging

LOG = logging.getLogger(__name__)

DEFERRED_INTERACTION_IDS = []


class DiscordUtils:
    @staticmethod
    async def reply(interaction: Interaction, *args, **kwargs):
        """Reply to an interaction regardless of if its been previously responded to"""
        if interaction.id in DEFERRED_INTERACTION_IDS:
            DEFERRED_INTERACTION_IDS.remove(interaction.id)
            return await interaction.followup.send(*args, **kwargs)
        if interaction.response.is_done():
            return await interaction.followup.send(*args, **kwargs)
        return await interaction.response.send_message(*args, **kwargs)

    @staticmethod
    async def defer(interaction: Interaction, *args, **kwargs):
        """Defer interaction response and hold interaction ID"""
        DEFERRED_INTERACTION_IDS.append(interaction.id)
        return await interaction.response.defer(*args, **kwargs)

    @staticmethod
    async def audit(
        interaction: Interaction, user: User, message, channel: TextChannel, color
    ):
        """Audit interaction in specified audit channel"""
        if channel is None:
            return LOG.error("Audit channel is not initialised")

        author = interaction.user.name
        authorID = interaction.user.id
        command = f"**Command:** /{interaction.command.parent.name} {interaction.command.name}"

        message = message.replace(f"{user.mention}", f"{user.name} (ID {user.id})")
        if "System message" not in message:
            message = message + "\n"

        embed = Embed(
            title=f"{author} (ID {authorID})",
            description=f"{message}\n{command}",
            color=color,
        )

        await channel.send(embed=embed)

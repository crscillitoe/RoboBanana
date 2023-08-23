from discord import Interaction


class DiscordUtils:
    @staticmethod
    async def reply(interaction: Interaction, *args, **kwargs):
        """Reply to an interaction regardless of if its been previously responded to"""
        if interaction.response.is_done():
            return await interaction.followup.send(*args, **kwargs)
        return await interaction.response.send_message(*args, **kwargs)

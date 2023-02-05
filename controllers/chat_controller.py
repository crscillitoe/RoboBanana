import discord
from discord import Interaction
from config import Config

# Sub role ids
Tier1 = int(Config.CONFIG["Discord"]["Tier1RoleID"])
Tier2 = int(Config.CONFIG["Discord"]["Tier2RoleID"])
Tier3 = int(Config.CONFIG["Discord"]["Tier3RoleID"])
GiftedTier1 = int(Config.CONFIG["Discord"]["GiftedTier1RoleID"])
GiftedTier2 = int(Config.CONFIG["Discord"]["GiftedTier2RoleID"])
GiftedTier3 = int(Config.CONFIG["Discord"]["GiftedTier3RoleID"])
sub_roles = {Tier1, Tier2, Tier3, GiftedTier1, GiftedTier2, GiftedTier3}


class ChatController:
    @staticmethod
    async def sub_only_chat(interaction: Interaction, enable: bool):
        roles = interaction.guild.roles
        overwrites = {}
        for role in roles:
            if not enable:
                overwrites[role] = discord.PermissionOverwrite(send_messages=True)
            else:
                if not sub_roles.__contains__(role.id):
                    overwrites[role] = discord.PermissionOverwrite(send_messages=False)
                else:
                    overwrites[role] = discord.PermissionOverwrite(send_messages=True)
        await interaction.channel.edit(overwrites=overwrites)
        sub_only_string = "Enabled" if enable else "Disabled"
        await interaction.response.send_message("Sub-only mode has been " + sub_only_string)
        return

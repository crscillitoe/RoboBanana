import discord
from discord import Interaction
from config import Config


# Sub role ids

DeafultRole = int(Config.CONFIG["Discord"]["defaultRoleID"])
Tier1 = int(Config.CONFIG["Discord"]["Tier1RoleID"])
Tier2 = int(Config.CONFIG["Discord"]["Tier2RoleID"])
Tier3 = int(Config.CONFIG["Discord"]["Tier3RoleID"])
GiftedTier1 = int(Config.CONFIG["Discord"]["GiftedTier1RoleID"])
GiftedTier2 = int(Config.CONFIG["Discord"]["GiftedTier2RoleID"])
GiftedTier3 = int(Config.CONFIG["Discord"]["GiftedTier3RoleID"])
roles = {Tier1, Tier2, Tier3, GiftedTier1, GiftedTier2, GiftedTier3,DeafultRole}

chat_modes = {
    "t3_only": {
        "allowed_roles": {Tier3, GiftedTier3},
        "slowmode": 0,
    },
    "normal": {
        "allowed_roles": roles,
        "slowmode": 15,
    },
    "t3_jail": {
        "allowed_roles": roles - {Tier3, GiftedTier3},
        "slowmode": 15,
    },
}

class ChatController:
    @staticmethod
    async def set_chat_mode(interaction: Interaction, mode: str):
        if mode not in chat_modes:
            await interaction.response.send_message(f"Invalid chat mode: {mode}")
            return
    
        chat_mode = chat_modes[mode]
        allowed_roles = chat_mode["allowed_roles"]
        slowmode = chat_mode["slowmode"]

        roles = interaction.guild.roles
        overwrites = {}
        for role in roles:
            if role.id in allowed_roles:
                overwrites[role] = discord.PermissionOverwrite(send_messages=True)
            else:
                overwrites[role] = discord.PermissionOverwrite(send_messages=False)
            


        await interaction.channel.edit(overwrites=overwrites, slowmode_delay=slowmode)
        await interaction.response.send_message(f"Chat mode set to {mode}")
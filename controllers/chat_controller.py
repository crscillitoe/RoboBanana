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

chat_modes = {
    "t3_only": {
        "allowed_roles": {Tier3, GiftedTier3},
        "disallowed_roles": None,
        "slowmode": 0,
    },
    "normal": {
        "allowed_roles": None,
        "disallowed_roles": None,
        "slowmode": 15,
    },
    "t3_jail": {
        "allowed_roles": None,
        "disallowed_roles": {Tier3, GiftedTier3},
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
        disallowed_roles = chat_mode["disallowed_roles"]
        slowmode = chat_mode["slowmode"]

        roles = interaction.guild.roles

        if allowed_roles is None:
            allowed_roles = {role.id for role in roles}
        if disallowed_roles is None:
            disallowed_roles = set()

        overwrites = {}

        # Set default overwrite for @everyone role
        everyone_role = interaction.guild.default_role
        overwrites[everyone_role] = discord.PermissionOverwrite(send_messages=False)

        for role in roles:
            if role.id in allowed_roles:
                overwrites[role] = discord.PermissionOverwrite(send_messages=True)
            if role.id in disallowed_roles:
                overwrites[role] = discord.PermissionOverwrite(send_messages=False)

        await interaction.channel.edit(overwrites=overwrites, slowmode_delay=slowmode)
        await interaction.response.send_message(f"Chat mode set to {mode}")

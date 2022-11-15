from __future__ import annotations
import asyncio
import logging
import discord
from discord import (
    app_commands,
    Client,
    Intents,
    Member,
    Message,
)
from commands.mod_commands import ModCommands
from commands.viewer_commands import ViewerCommands
from config import Config
from db import DB

discord.utils.setup_logging(level=logging.INFO, root=True)

STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
WELCOME_CHAT_ID = int(Config.CONFIG["Discord"]["WelcomeChannel"])
PENDING_REWARDS_CHAT_ID = int(Config.CONFIG["Discord"]["PendingRewardChannel"])
GUILD_ID = int(Config.CONFIG["Discord"]["GuildID"])
PREMIUM_IDS = list(map(int, [
    Config.CONFIG["Discord"]["Tier1RoleID"],
    Config.CONFIG["Discord"]["Tier2RoleID"],
    Config.CONFIG["Discord"]["Tier3RoleID"],
]))


class RaffleBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True

        super().__init__(intents=intents)

    async def on_ready(self):
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")
        # guild = discord.Object(id=GUILD_ID)
        # tree.clear_commands(guild=guild)
        # tree.copy_global_to(guild=guild)
        # await tree.sync(guild=guild)

    async def on_message(self, message: Message):
        # Don't respond to ourselves
        if message.author == self.user:
            return

        # Only look in the active stream channel
        if message.channel.id == STREAM_CHAT_ID:
            DB().accrue_channel_points(message.author.id, message.author.roles)

    async def on_member_update(self, before: Member, after: Member):
        new_roles = set(after.roles) - set(before.roles)
        if len(new_roles) == 0:
            return

        for role in new_roles:
            if role.id not in PREMIUM_IDS:
                continue

            return await self.get_channel(STREAM_CHAT_ID).send(
                f"Thank you {after.mention} for joining {role.name}!"
            )

client = RaffleBot()
tree = app_commands.CommandTree(client)


@client.event
async def on_guild_join(guild):
    tree.clear_commands(guild=guild)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)


async def main():
    async with client:
        tree.add_command(ModCommands(tree, client))
        tree.add_command(ViewerCommands(tree, client))
        await client.start(Config.CONFIG["Discord"]["Token"])


if __name__ == "__main__":
    asyncio.run(main())

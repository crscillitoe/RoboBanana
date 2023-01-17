from __future__ import annotations
import asyncio
import logging
import discord
from discord import (
    app_commands,
    Client,
    Intents,
    Message,
)
from commands.mod_commands import ModCommands
from commands.viewer_commands import ViewerCommands
from commands.manager_commands import ManagerCommands
from config import Config
from controllers.sub_controller import SubController
from db import DB

discord.utils.setup_logging(level=logging.INFO, root=True)

STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
WELCOME_CHAT_ID = int(Config.CONFIG["Discord"]["WelcomeChannel"])
PENDING_REWARDS_CHAT_ID = int(Config.CONFIG["Discord"]["PendingRewardChannel"])
GUILD_ID = int(Config.CONFIG["Discord"]["GuildID"])
SERVER_SUBSCRIPTION_MESSAGE_TYPE = 25


class RaffleBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True

        # initialize DB for the first time
        DB()

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

        # Server Subscription message
        if (
            message.channel.id == WELCOME_CHAT_ID
            and message.type.value == SERVER_SUBSCRIPTION_MESSAGE_TYPE
        ):
            await SubController.subscribe(message, self)

        # Only look in the active stream channel
        if message.channel.id == STREAM_CHAT_ID:
            DB().accrue_channel_points(message.author.id, message.author.roles)


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
        tree.add_command(ManagerCommands(tree, client))
        await client.start(Config.CONFIG["Discord"]["Token"])


if __name__ == "__main__":
    asyncio.run(main())

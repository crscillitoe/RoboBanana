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
from config import Config
from db import DB

discord.utils.setup_logging(level=logging.INFO, root=True)

STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
WELCOME_CHAT_ID = int(Config.CONFIG["Discord"]["WelcomeChannel"])
PENDING_REWARDS_CHAT_ID = int(Config.CONFIG["Discord"]["PendingRewardChannel"])
GUILD_ID = int(Config.CONFIG["Discord"]["GuildID"])


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

    async def on_button_click(self, interaction):
        logging.info(f"button clicked: {interaction}")

    async def on_message(self, message: Message):
        # Don't respond to ourselves
        if message.author == self.user:
            return
        # Only look in the active stream channel
        channels_to_listen_to = {STREAM_CHAT_ID, WELCOME_CHAT_ID}
        if message.channel.id not in channels_to_listen_to:
            return

        if message.channel.id == STREAM_CHAT_ID:
            DB().accrue_channel_points(message.author.id, message.author.roles)

        if message.channel.id == WELCOME_CHAT_ID:
            premium_ids = map(
                int,
                [
                    Config.CONFIG["Discord"]["Tier1RoleID"],
                    Config.CONFIG["Discord"]["Tier2RoleID"],
                    Config.CONFIG["Discord"]["Tier3RoleID"],
                ],
            )

            role_name = None
            for role_id in premium_ids:
                role = discord.utils.get(message.author.roles, id=role_id)
                if role is not None:
                    role_name = role.name
                    break

            if role_name is not None:
                await self.get_channel(STREAM_CHAT_ID).send(
                    f"Thank you {message.author.mention} for joining {role_name}!"
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

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
PREMIUM_IDS = list(map(int, [
    Config.CONFIG["Discord"]["Tier1RoleID"],
    Config.CONFIG["Discord"]["Tier2RoleID"],
    Config.CONFIG["Discord"]["Tier3RoleID"],
]))
SERVER_SUBSCRIPTION_MESSAGE_TYPE = 25

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

        # Server Subscription message
        if message.channel.id == WELCOME_CHAT_ID and message.type.value == SERVER_SUBSCRIPTION_MESSAGE_TYPE:
            # fetch extra attached message info
            raw_msg = await self.http.get_message(channel_id=message.channel.id, message_id=message.id)

            role_sub_data = raw_msg.get("role_subscription_data")
            if role_sub_data is None:
                return logging.error(f"Unable to get role subscription data for message: {message.id}")

            # comes in like this -> 'tier_name': 'THE ONES WHO KNOW membership',
            # trim " membership" and get the actual role
            role_name = role_sub_data.get("tier_name", "").rstrip(" membership")
            role = next(filter(lambda x: x.name.startswith(role_name) and x.id in PREMIUM_IDS, message.guild.roles), None)
            if role is None:
                return logging.error(f"Unable to get role starting with: {role_name}")

            # create the thank you message
            if role_sub_data.get("is_renewal", False):
                num_months = role_sub_data.get("total_months_subscribed", 1)
                thankyou_message = f"Thank you {message.author.mention} for resubscribing to {role.name} for {num_months} months!"
            else:
                thankyou_message = f"Thank you {message.author.mention} for subscribing to {role.name}!"

            return await self.get_channel(STREAM_CHAT_ID).send(thankyou_message)

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
        await client.start(Config.CONFIG["Discord"]["Token"])


if __name__ == "__main__":
    asyncio.run(main())

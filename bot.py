from __future__ import annotations
import asyncio
from datetime import timedelta
import logging
import requests
import discord
from discord import (
    Member,
    User,
    app_commands,
    Client,
    Intents,
    Message,
    Reaction,
)
from commands.meme_commands import MemeCommands
from commands.mod_commands import ModCommands
from commands.overlay_commands import OverlayCommands
from commands.point_history_commands import PointHistoryCommands
from commands.sync_commands import SyncCommands
from commands.temprole_commands import TemproleCommands
from commands.viewer_commands import ViewerCommands
from commands.manager_commands import ManagerCommands
from commands.reaction_commands import ReactionCommands
from commands.vod_commands import VodCommands
from config import YAMLConfig as Config
from controllers.reaction_controller import ReactionController
from controllers.sub_controller import SubController
from controllers.temprole_controller import TempRoleController
from db import DB
from threading import Thread
from util.discord_utils import DiscordUtils
from util.server_utils import get_base_url
from util.sync_utils import SyncUtils


discord.utils.setup_logging(level=logging.INFO, root=True)

COOL_URL = f"{get_base_url()}/publish-cool"
COOL_ID = Config.CONFIG["Discord"]["CoolMeter"]["CoolEmoji"]
UNCOOL_ID = Config.CONFIG["Discord"]["CoolMeter"]["UncoolEmoji"]
AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]
STREAM_CHAT_ID = Config.CONFIG["Discord"]["Channels"]["Stream"]
WELCOME_CHAT_ID = Config.CONFIG["Discord"]["Channels"]["Welcome"]
PENDING_REWARDS_CHAT_ID = Config.CONFIG["Discord"]["ChannelPoints"][
    "PendingRewardChannel"
]
GUILD_ID = Config.CONFIG["Discord"]["GuildID"]
CROWD_MUTE_EMOJI_ID = Config.CONFIG["Discord"]["CrowdMute"]["Emoji"]
CROWD_MUTE_THRESHOLD = Config.CONFIG["Discord"]["CrowdMute"]["Threshold"]
CROWD_MUTE_DURATION = Config.CONFIG["Discord"]["CrowdMute"]["Duration"]
FOSSA_BOT_ID = 488164251249279037
SERVER_SUBSCRIPTION_MESSAGE_TYPE = 25
MAX_CHARACTER_LENGTH = 200

LOG = logging.getLogger(__name__)


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
        SubController(self).send_count.start()
        SubController(self).sync_channel_perms.start()
        TempRoleController(self).expire_roles.start()

    async def on_message_edit(self, before: Message, message: Message):
        # Don't respond to ourselves
        if message.author == self.user:
            return

        # Only look in the active stream channel
        if message.channel.id == STREAM_CHAT_ID:
            await self.check_message_length(message)

    async def check_message_length(self, message: Message):
        # Ethan check
        if message.author.id == 204343692960464896:
            return

        length = len(message.content)
        if length > MAX_CHARACTER_LENGTH:
            content = message.content
            await message.delete()
            await message.author.send(
                "Hey! Keep your messages in the stream chat under"
                f" {MAX_CHARACTER_LENGTH} characters please! Your message was"
                f" {length} characters long! Thanks! Here's your message: {content}."
            )

    async def on_message(self, message: Message):
        # Don't respond to ourselves
        if message.author == self.user or message.author.id == FOSSA_BOT_ID:
            return

        asyncio.get_event_loop().create_task(
            ReactionController.apply_reactions(message)
        )

        # Server Subscription message
        if (
            message.channel.id == WELCOME_CHAT_ID
            and message.type.value == SERVER_SUBSCRIPTION_MESSAGE_TYPE
        ):
            await SubController.subscribe(message, self)

        # Only look in the active stream channel
        if message.channel.id == STREAM_CHAT_ID:
            await self.check_message_length(message)

            DB().accrue_channel_points(message.author.id, message.author.roles)
            cool = str(COOL_ID) in message.content
            uncool = str(UNCOOL_ID) in message.content
            if cool and not uncool:
                Thread(
                    target=publish_cool,
                    args=(1,),
                ).start()
            elif uncool and not cool:
                Thread(
                    target=publish_cool,
                    args=(-1,),
                ).start()

    async def on_reaction_add(self, reaction: Reaction, user: Member | User):
        if isinstance(reaction.emoji, str):
            return
        if reaction.emoji.id != CROWD_MUTE_EMOJI_ID:
            return
        if reaction.count < CROWD_MUTE_THRESHOLD:
            return

        if reaction.count == CROWD_MUTE_THRESHOLD:
            mute_reason = (
                "been crowd muted for 10 minutes, likely due to asking:"
                " "
                " 1. An easily Googleable question"
                " "
                " 2. A question about aim (see <#1056639643443007659>)"
                " "
                " 3. A question answered directly within our <#1035739990413545492>."
            )
            await reaction.message.author.timeout(
                timedelta(minutes=CROWD_MUTE_DURATION), reason=f"You have {mute_reason}"
            )
            await reaction.message.reply(f"This user has {mute_reason}")


client = RaffleBot()
tree = app_commands.CommandTree(client)


@client.event
async def on_guild_join(guild):
    tree.clear_commands(guild=guild)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)


def publish_cool(cool: int):
    payload = {"cool": cool}
    response = requests.post(
        url=COOL_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )
    if response.status_code != 200:
        LOG.error(f"Failed to publish sub summary: {response.text}")


async def main():
    async with client:
        tree.add_command(SyncCommands(tree, client))
        SyncUtils.add_commands_to_tree(tree, client)
        await client.start(Config.CONFIG["Secrets"]["Discord"]["Token"])


if __name__ == "__main__":
    asyncio.run(main())

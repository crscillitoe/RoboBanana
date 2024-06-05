from __future__ import annotations
import asyncio
from datetime import timedelta
import logging
import time
import requests
import discord
from discord import (
    Member,
    Role,
    User,
    app_commands,
    Client,
    Intents,
    Message,
    Reaction,
)
from commands import sync_commands
from commands import mod_commands
from commands import viewer_commands
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
from controllers.good_morning_controller import GoodMorningController
from db import DB
from threading import Thread
from util.discord_utils import DiscordUtils
from util.server_utils import get_base_url
from util.sync_utils import SyncUtils
import re


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
TIER3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["Tier3Role"]
GIFTED_TIER3_ROLE = Config.CONFIG["Discord"]["Subscribers"]["GiftedTier3Role"]
# HIDDEN_MOD_ROLE should be 1040337265790042172 when committing and refers to the Mod (Role Hidden)
# STAFF_DEVELOPER_ROLE should be 1226317841272279131 when committing and refers to the Staff Developer role
HIDDEN_MOD_ROLE = 1040337265790042172
STAFF_DEVELOPER_ROLE = 1226317841272279131
FOSSA_BOT_ID = 488164251249279037
SERVER_SUBSCRIPTION_MESSAGE_TYPE = 25
CUSTOM_EMOJI_PATTERN = re.compile("(<a?:(\w+):\d{17,19}>?)")
MAX_EMOJI_COUNT = 5

MAX_CHARACTER_LENGTH = 200
ROLE_AND_USER_OVERRIDE: dict[str, int] = {
    STAFF_DEVELOPER_ROLE: 300,
    Config.CONFIG["Discord"]["Roles"]["Mod"]: 400,
    HIDDEN_MOD_ROLE: 400,
    1237760496191537176: 400,  # Hooj's Accountant
    204343692960464896: 9999,  # Ethan
}

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
        sync_commands.UPTIME_START_TIME = time.time()
        # guild = discord.Object(id=GUILD_ID)
        # tree.clear_commands(guild=guild)
        # tree.copy_global_to(guild=guild)
        # await tree.sync(guild=guild)
        SubController(self).send_count.start()
        # Disable opening / closing inhouse queues at Ethan's request
        # Leaving here for posterity
        # SubController(self).sync_channel_perms.start()
        TempRoleController(self).expire_roles.start()
        GoodMorningController(self).auto_reward_users.start()
        mod_commands.remove_inactive_chatters.start()

    async def on_message_edit(self, before: Message, message: Message):
        # Don't respond to ourselves
        if message.author == self.user:
            return

        # Only look in the active stream channel
        if message.channel.id == STREAM_CHAT_ID:
            await self.check_message_length(message)

    async def check_message_length(self, message: Message):
        # The content we get might contain custom emoji, which will be displayed like this: <:hoojKEKW:1059961649412460575>
        # Since an emoji isn't actually that long (the ID and brackets are 20+ chars), we run a regex to count emoji and remove 20*x chars from the length for leniency
        clean_content = message.clean_content
        custom_emoji_matches = dict(
            (full_match, name)
            for full_match, name in re.findall(CUSTOM_EMOJI_PATTERN, clean_content)
        )
        for match in custom_emoji_matches:
            clean_content = clean_content.replace(match, custom_emoji_matches[match])

        custom_emoji_count = len(custom_emoji_matches)
        length = len(clean_content)

        user_max_length = get_length_for_user(message.author.roles, message.author.id)
        if length > user_max_length:
            content = message.content
            await message.delete()
            await message.author.send(
                "Hey! Keep your messages in the stream chat under"
                f" {user_max_length} characters please! Your message was"
                f" {length} characters long! Thanks! Here's your message: {content}."
            )
        if custom_emoji_count > MAX_EMOJI_COUNT:
            content = message.content
            await message.delete()
            await message.author.send(
                "Hey! Keep your emoji count for messages in the stream chat under"
                f" {MAX_EMOJI_COUNT} emoji please! Your message included"
                f" {custom_emoji_count} emoji! Thanks! Here's your message: {content}."
            )

    async def on_message(self, message: Message):
        # Don't respond to ourselves
        if message.author == self.user or message.author.id == FOSSA_BOT_ID:
            return

        # Gen Alpha Role Custom Rules
        if any(role.id in [1245138880626425866] for role in message.author.roles):
            brainrot = likely_brain_rot(message)
            if brainrot[0]:
                await message.channel.send(
                    f"{message.author.mention} used a cringe word: {brainrot[1]}. I've timed them out for a minute."
                )
                await message.author.timeout(
                    timedelta(minutes=1),
                    reason=f"Gen Alpha cringe detected: {brainrot[1]}",
                )

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

            if viewer_commands.ACTIVE_CHATTER_KEYWORD is not None:
                if viewer_commands.ACTIVE_CHATTER_KEYWORD in message.content:
                    mod_commands.ACTIVE_CHATTERS[message.author.id] = time.time()
                    if any(
                        role.id in [TIER3_ROLE, GIFTED_TIER3_ROLE]
                        for role in message.author.roles
                    ):
                        mod_commands.ACTIVE_T3_CHATTERS[message.author.id] = time.time()
            else:
                mod_commands.ACTIVE_CHATTERS[message.author.id] = time.time()
                if any(
                    role.id in [TIER3_ROLE, GIFTED_TIER3_ROLE]
                    for role in message.author.roles
                ):
                    mod_commands.ACTIVE_T3_CHATTERS[message.author.id] = time.time()

    async def on_reaction_add(self, reaction: Reaction, user: Member | User):
        await ReactionController.apply_crowd_mute(reaction)

    async def on_member_update(self, before: Member, after: Member):
        removed_roles = set(before.roles) - set(after.roles)
        if removed_roles:
            removed_roles = [role.id for role in removed_roles]
            await TempRoleController.check_removed_roles(removed_roles, after, GUILD_ID)


def likely_brain_rot(message: Message) -> (bool, str):
    content = message.content

    # No leet speak here.
    content = content.replace("1", "i")
    content = content.replace("3", "e")
    content = content.replace("4", "a")
    content = content.replace("5", "s")
    content = content.replace("0", "o")
    content = content.replace("7", "t")
    content = content.replace("$", "s")
    content = content.replace("|", "l")
    content = content.replace("/", "l")
    content = content.replace("\\", "l")
    content = content.replace("*", "")

    brainrot = [
        build_regex("sigma"),
        build_regex("omega"),
        build_regex("skibidi"),
        build_regex("gyat"),
        build_regex("rizz"),
        build_regex("boomer"),
        build_regex("ohio"),
        build_regex("cope"),
        build_regex("ratio"),
        build_regex("bussin"),
        build_regex("mewing"),
        build_regex("gronk"),
        build_regex("jelq"),
        build_regex("griddy"),
        build_regex("ligma"),
        build_regex("imposter"),
        build_regex("amogus"),
        build_regex("fanum"),
        build_regex("maxxing"),
        build_regex("Σ"),
        build_regex("erm what the"),
        build_regex("erm, what the"),
        build_regex("chat"),
        build_regex("is this real"),
    ]

    for rot in brainrot:
        found = re.findall(rot, content)
        if len(found) > 0:
            return (True, rot)

    return (False, "")


def build_regex(cringe_word: str) -> str:
    to_return = "(?i)"
    for c in cringe_word:
        if c == "l" or c == "i":
            to_return += "(l|i)" + "+"
        else:
            to_return += c + "+"

    return to_return


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


def get_length_for_user(roles: list[Role], user_id: int) -> int:
    for id, override in sorted(
        ROLE_AND_USER_OVERRIDE.items(), key=lambda item: item[1], reverse=True
    ):
        if user_id == id:
            return override
        role = discord.utils.get(roles, id=id)
        if role is not None:
            return override
    return MAX_CHARACTER_LENGTH


async def main():
    async with client:
        tree.add_command(SyncCommands(tree, client))
        SyncUtils.add_commands_to_tree(tree, client)
        await client.start(Config.CONFIG["Secrets"]["Discord"]["Token"])


if __name__ == "__main__":
    asyncio.run(main())

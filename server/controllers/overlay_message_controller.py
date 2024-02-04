from bot import AUTH_TOKEN
from config import YAMLConfig as Config
from server.blueprints.sse import sse
from server.util.constants import CHAT_MESSAGE_STREAM_TYPE, EVENTS_CHANNEL
from server.util.discord_client import DISCORD_CLIENT
import logging
import requests
from discord import AllowedMentions

from util.server_utils import get_base_url

LOG = logging.getLogger(__name__)

DISCORD_IDENTITY_ENDPOINT = "https://discord.com/api/v10/users/@me"
EXPIRES_IN = 604800
USER_ID_CACHE = dict()
GUILD_ID = Config.CONFIG["Discord"]["GuildID"]
PUBLISH_URL = f"{get_base_url()}/publish-chat"


class OverlayMessageController:
    @staticmethod
    def _get_user_id(token):
        if token in USER_ID_CACHE:
            return USER_ID_CACHE[token]
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(DISCORD_IDENTITY_ENDPOINT, headers=headers)
        user_id = int(response.json()["id"])
        USER_ID_CACHE[token] = user_id
        return user_id

    @staticmethod
    async def send_message(message: str, token: str):
        user_id = OverlayMessageController._get_user_id(token)
        guild = DISCORD_CLIENT.get_guild(GUILD_ID)
        if guild is None:
            LOG.error(f"Failed to find guild with ID: {GUILD_ID}")
            return

        member = guild.get_member(user_id)
        if member is None:
            return

        if member.is_timed_out():
            return

        # Ugly check for T3 subs for now, feature is not complete and I don't want
        # to deal with the army of users explaining to me why it's 'broken'
        t3_role = Config.CONFIG["Discord"]["Subscribers"]["Tier3Role"]
        gifted_t3_role = Config.CONFIG["Discord"]["Subscribers"]["GiftedTier3Role"]
        twitch_t3_role = Config.CONFIG["Discord"]["Subscribers"]["TwitchTier3Role"]

        valid_roles = [t3_role, gifted_t3_role, twitch_t3_role]

        can_send = False
        for role in member.roles:
            if role.id in valid_roles:
                can_send = True
                break
        if not can_send:
            return

        to_send = {
            "content": message,
            "displayName": member.display_name,
            "roles": [
                {
                    "colorR": r.color.r,
                    "colorG": r.color.g,
                    "colorB": r.color.b,
                    "icon": None if r.icon is None else r.icon.url,
                    "id": r.id,
                    "name": r.name,
                }
                for r in member.roles
            ],
            "stickers": [],
            "emojis": [],
            "mentions": [],
            "author_id": user_id,
            "platform": "overlay",
        }

        # stream_channel = Config.CONFIG["Discord"]["Channels"]["Stream"]
        # await DISCORD_CLIENT.get_channel(stream_channel).send(
        #     f"[<@{user_id}>] {message.replace('@', '')}",
        #     suppress_embeds=True,
        #     allowed_mentions=AllowedMentions.none(),
        # )

        await publish_chat(to_send)


async def publish_chat(chat_message):
    try:
        await sse.publish(
            chat_message, type=CHAT_MESSAGE_STREAM_TYPE, channel=EVENTS_CHANNEL
        )
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)

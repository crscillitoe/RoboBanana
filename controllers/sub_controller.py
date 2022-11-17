from threading import Thread
from discord import Message, Client
from config import Config
import logging
import discord
import requests

STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
AUTH_TOKEN = Config.CONFIG["Server"]["AuthToken"]
PUBLISH_URL = "http://localhost:3000/publish-sub"

LOG = logging.getLogger(__name__)


class SubController:
    @staticmethod
    async def subscribe(message: Message, client: Client):
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
            await client.get_channel(STREAM_CHAT_ID).send(
                f"Thank you {message.author.mention} for joining {role_name}!"
            )
            Thread(
                target=publish_update,
                args=(
                    message.author.name,
                    role_name,
                ),
            ).start()


def publish_update(name: str, role_name: str):
    payload = {
        "name": name,
        "tier": role_name,
    }
    response = requests.post(
        url=PUBLISH_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )
    if response.status_code != 200:
        LOG.error(f"Failed to publish sub summary: {response.text}")

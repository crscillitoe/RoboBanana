from threading import Thread
from discord import Message, Client
from config import Config
import logging
import discord
import requests

STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
AUTH_TOKEN = Config.CONFIG["Server"]["AuthToken"]
PUBLISH_URL = "http://localhost:3000/publish-sub"
PREMIUM_IDS = list(map(int, [
    Config.CONFIG["Discord"]["Tier1RoleID"],
    Config.CONFIG["Discord"]["Tier2RoleID"],
    Config.CONFIG["Discord"]["Tier3RoleID"],
]))

LOG = logging.getLogger(__name__)


class SubController:
    @staticmethod
    async def subscribe(message: Message, client: Client):
        # fetch extra attached message info
        raw_msg = await client.http.get_message(channel_id=message.channel.id, message_id=message.id)

        role_sub_data = raw_msg.get("role_subscription_data")
        if role_sub_data is None:
            return LOG.error(f"Unable to get role subscription data for message: {message.id}")

        # comes in like this -> 'tier_name': 'THE ONES WHO KNOW membership',
        # trim " membership" and get the actual role
        membership_name = role_sub_data.get("tier_name", "").rstrip(" membership")
        role = next(filter(lambda x: x.name.startswith(membership_name) and x.id in PREMIUM_IDS, message.guild.roles), None)
        if role is None:
            return LOG.error(f"Unable to get role starting with: {membership_name}")

        role_name = role.name

        # create the thank you message
        if role_sub_data.get("is_renewal", False):
            num_months = role_sub_data.get("total_months_subscribed", 1)
            thankyou_message = f"Thank you {message.author.mention} for resubscribing to {role_name} for {num_months} months!"
        else:
            thankyou_message = f"Thank you {message.author.mention} for subscribing to {role_name}!"

        await client.get_channel(STREAM_CHAT_ID).send(thankyou_message)
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

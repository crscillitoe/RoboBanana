from threading import Thread
from discord import Message, Client
from discord.ext import tasks
import discord.utils
from config import Config
import logging
import requests
from datetime import datetime
import pytz

STREAM_CHAT_ID = int(Config.CONFIG["Discord"]["StreamChannel"])
BOT_AUDIT_CHANNEL = int(Config.CONFIG["Discord"]["PointsAuditChannel"])
AUTH_TOKEN = Config.CONFIG["Server"]["AuthToken"]
PUBLISH_URL = "http://localhost:3000/publish-sub"
PUBLISH_COUNT_URL = "http://localhost:3000/publish-sub-count"
PREMIUM_IDS = list(
    map(
        int,
        [
            Config.CONFIG["Discord"]["Tier1RoleID"],
            Config.CONFIG["Discord"]["Tier2RoleID"],
            Config.CONFIG["Discord"]["Tier3RoleID"],
        ],
    )
)

LOG = logging.getLogger(__name__)


class SubController:
    def __init__(self, client: Client) -> None:
        self.client = client

    @staticmethod
    async def subscribe(message: Message, client: Client):
        # fetch extra attached message info
        raw_msg = await client.http.get_message(
            channel_id=message.channel.id, message_id=message.id
        )

        # 6 Month T3
        t3_6_month_role = message.guild.get_role(1087797719919235123)

        role_sub_data = raw_msg.get("role_subscription_data")
        if role_sub_data is None:
            return LOG.error(
                f"Unable to get role subscription data for message: {message.id}"
            )

        # comes in like this -> 'tier_name': 'THE ONES WHO KNOW membership',
        # trim " membership" and get the actual role
        membership_name = role_sub_data.get("tier_name", "").rstrip(" membership")
        role = next(
            filter(
                lambda x: x.name.startswith(membership_name) and x.id in PREMIUM_IDS,
                message.guild.roles,
            ),
            None,
        )
        if role is None:
            return LOG.error(f"Unable to get role starting with: {membership_name}")

        role_name = role.name

        name_prefix = "Thank you {name}"
        # create the thank you message
        if role_sub_data.get("is_renewal", False):
            num_months = role_sub_data.get("total_months_subscribed", 1)
            thankyou_message = (
                f"{name_prefix} for resubscribing to {role_name} for"
                f" {num_months} months!"
            )
        else:
            thankyou_message = f"{name_prefix} for subscribing to {role_name}!"

        author_name = (
            message.author.nick
            if message.author.nick is not None
            else message.author.name
        )
        mention_thankyou = thankyou_message.format(name=message.author.mention)
        name_thankyou = thankyou_message.format(name=author_name)

        if "6 months" in mention_thankyou and "THE ONES WHO" in mention_thankyou:
            await message.author.add_roles(t3_6_month_role)

        Thread(
            target=publish_update,
            args=(
                message.author.name,
                role_name,
                name_thankyou,
            ),
        ).start()
        await client.get_channel(BOT_AUDIT_CHANNEL).send(mention_thankyou)

    @tasks.loop(minutes=5.0)
    async def sync_channel_perms(self):
        # Dear god, forgive me for the dark arts I am about to use
        # to smite my logical problem solving issues into oblivion.

        # Grab the day of the year... in FUCKING HONOLULU POG
        # NA INHOUSES MORE LIKE HAWAIIAN INHOUSES
        # Example: July 31st --> 212
        day_of_year_hawaii = datetime.now(pytz.timezone('US/Hawaii')).timetuple().tm_yday


        # this variable is very clear.
        day_of_year_east_brazil = datetime.now(pytz.timezone('Brazil/East')).timetuple().tm_yday

        # GIVE IT UP FOR THE EVEN DAYS BABY WOOOO
        na_queues_open = day_of_year_hawaii % 2 == 0

        # Except EU likes odd days because brazil is a day behind EU
        eu_queues_open = day_of_year_east_brazil % 2 == 1

        # normal stuff here
        guild = await self.client.fetch_guild(Config.CONFIG["Discord"]["GuildID"])

        t3_role_role = guild.get_role(1036807951484203099)
        gifted_t3_role = guild.get_role(1045466382470484040)
        twitch_t3 = guild.get_role(935319103302926409)
        t3_subs = [t3_role_role, gifted_t3_role, twitch_t3]

        na_inhouses = self.client.get_channel(1118272266988441630)
        eu_inhouses = self.client.get_channel(1074056805275140308)

        for t3 in t3_subs:
            await na_inhouses.set_permissions(
                t3, view_channel=na_queues_open
            )

            await eu_inhouses.set_permissions(
                t3, view_channel=eu_queues_open
            )


    @tasks.loop(minutes=1.0)
    async def send_count(self):
        guild = await self.client.fetch_guild(Config.CONFIG["Discord"]["GuildID"])
        guild_members = guild.fetch_members(limit=None)

        premium_id_count = {}
        async for member in guild_members:
            for role_id in PREMIUM_IDS:
                if discord.utils.get(member.roles, id=role_id):
                    premium_id_count[role_id] = premium_id_count.get(role_id, 0) + 1

        tier_1_count, tier_2_count, tier_3_count = [
            premium_id_count[role_id] for role_id in PREMIUM_IDS
        ]

        Thread(
            target=publish_count,
            args=(
                tier_1_count,
                tier_2_count,
                tier_3_count,
            ),
        ).start()


def publish_update(name: str, role_name: str, message: str):
    payload = {"name": name, "tier": role_name, "message": message}
    response = requests.post(
        url=PUBLISH_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )
    if response.status_code != 200:
        LOG.error(f"Failed to publish sub summary: {response.text}")


def publish_count(tier_1_count: int, tier_2_count: int, tier_3_count: int):
    payload = {
        "tier1Count": tier_1_count,
        "tier2Count": tier_2_count,
        "tier3Count": tier_3_count,
    }
    response = requests.post(
        url=PUBLISH_COUNT_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )
    if response.status_code != 200:
        LOG.error(f"Failed to publish sub count: {response.text}")

from collections import namedtuple
from operator import attrgetter
from threading import Thread
from typing import Optional
from discord import Colour, Embed, Message, Client
from discord.ext import tasks
import discord.utils
from config import YAMLConfig as Config
from controllers.temprole_controller import TempRoleController
from util.server_utils import get_base_url
import logging
import requests
from datetime import datetime
import pytz

STREAM_CHAT_ID = Config.CONFIG["Discord"]["Channels"]["Stream"]
BOT_AUDIT_CHANNEL = Config.CONFIG["Discord"]["ChannelPoints"]["PointsAuditChannel"]
SIX_MONTH_TIER_3_ROLE_ID = Config.CONFIG["Discord"]["Subscribers"]["6MonthTier3Role"]
TWELVE_MONTH_TIER_3_ROLE_ID = Config.CONFIG["Discord"]["Subscribers"][
    "12MonthTier3Role"
]
TIER_3_ROLE_ID = Config.CONFIG["Discord"]["Subscribers"]["Tier3Role"]
EIGHTEEN_MONTH_TIER_3_ROLE_ID = Config.CONFIG["Discord"]["Subscribers"][
    "18MonthTier3Role"
]
GIFTED_TIER_3_ROLE_ID = Config.CONFIG["Discord"]["Subscribers"]["GiftedTier3Role"]
TWITCH_TIER_3_ROLE_ID = Config.CONFIG["Discord"]["Subscribers"]["TwitchTier3Role"]
NA_OPEN_INHOUSE_CHANNEL_ID = Config.CONFIG["Discord"]["Inhouses"]["NAOpenChannel"]
EU_OPEN_INHOUSE_CHANNEL_ID = Config.CONFIG["Discord"]["Inhouses"]["EUOpenChannel"]
GUILD_ID = Config.CONFIG["Discord"]["GuildID"]

AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]
PUBLISH_URL = f"{get_base_url()}/publish-sub"
PUBLISH_COUNT_URL = f"{get_base_url()}/publish-sub-count"
PREMIUM_IDS = list(
    map(
        int,
        [
            Config.CONFIG["Discord"]["Subscribers"]["Tier1Role"],
            Config.CONFIG["Discord"]["Subscribers"]["Tier2Role"],
            Config.CONFIG["Discord"]["Subscribers"]["Tier3Role"],
        ],
    )
)

SubDurationReward = namedtuple("SubDurationReward", "duration role_id")

SUB_DURATION_REWARDS = sorted(
    [
        SubDurationReward(duration=18, role_id=EIGHTEEN_MONTH_TIER_3_ROLE_ID),
        SubDurationReward(duration=12, role_id=TWELVE_MONTH_TIER_3_ROLE_ID),
        SubDurationReward(duration=6, role_id=SIX_MONTH_TIER_3_ROLE_ID),
    ],
    key=attrgetter("duration"),
    reverse=True,
)

LOG = logging.getLogger(__name__)


class SubController:
    def __init__(self, client: Client) -> None:
        self.client = client

    @staticmethod
    def _get_months_subscribed(role_sub_data: dict):
        return role_sub_data.get("total_months_subscribed", 1)

    @staticmethod
    def _get_duration_reward_role(
        num_months_subscribed: int, mention_thankyou: str
    ) -> Optional[int]:
        if "THE ONES WHO" not in mention_thankyou:
            return None
        for duration, role_id in SUB_DURATION_REWARDS:
            if num_months_subscribed >= duration:
                return role_id
        return None

    @staticmethod
    async def _assign_duration_reward(
        client: Client,
        message: Message,
        num_months_subscribed: int,
        mention_thankyou: str,
    ):
        role_id = SubController._get_duration_reward_role(
            num_months_subscribed, mention_thankyou
        )
        if role_id is None:
            return

        duration_reward_role = message.guild.get_role(role_id)
        success, message = await TempRoleController.set_role(
            message.author, duration_reward_role, "31 days"
        )

        if not success:
            fail_embed = Embed(
                title="Failed to assign duration reward role",
                description=message,
                color=Colour.red(),
            )
            return await client.get_channel(BOT_AUDIT_CHANNEL).send(embed=fail_embed)

        # Always assign the 6 month role, this is to ensure there is a shared
        # Role across all longer term T3 subs that we can use for embed permissions and
        # Other things, such as pinging all longer term subscribers easily.
        six_month = message.guild.get_role(SIX_MONTH_TIER_3_ROLE_ID)
        success, message = await TempRoleController.set_role(
            message.author, six_month, "31 days"
        )

        if not success:
            fail_embed = Embed(
                title="Failed to assign duration reward role",
                description=message,
                color=Colour.red(),
            )
            return await client.get_channel(BOT_AUDIT_CHANNEL).send(embed=fail_embed)

        embed = Embed(
            title="Assigned Temprole",
            description=message,
            color=Colour.green(),
        )
        await client.get_channel(BOT_AUDIT_CHANNEL).send(embed=embed)

    @staticmethod
    async def subscribe(message: Message, client: Client):
        # fetch extra attached message info
        raw_msg = await client.http.get_message(
            channel_id=message.channel.id, message_id=message.id
        )

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
        num_months_subscribed = SubController._get_months_subscribed(role_sub_data)
        if role_sub_data.get("is_renewal", False):
            thankyou_message = (
                f"{name_prefix} for resubscribing to {role_name} for"
                f" {num_months_subscribed} months!"
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
        await SubController._assign_duration_reward(
            client, message, num_months_subscribed, mention_thankyou
        )

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
        day_of_year_hawaii = (
            datetime.now(pytz.timezone("US/Hawaii")).timetuple().tm_yday
        )

        # this variable is very clear.
        day_of_year_east_brazil = (
            datetime.now(pytz.timezone("Brazil/East")).timetuple().tm_yday
        )

        # GIVE IT UP FOR THE EVEN DAYS BABY WOOOO
        na_queues_open = day_of_year_hawaii % 2 == 0

        # Except EU likes odd days because brazil is a day behind EU
        eu_queues_open = day_of_year_east_brazil % 2 == 1

        # normal stuff here
        guild = await self.client.fetch_guild(GUILD_ID)
        t3_role_role = guild.get_role(TIER_3_ROLE_ID)
        gifted_t3_role = guild.get_role(GIFTED_TIER_3_ROLE_ID)
        twitch_t3 = guild.get_role(TWITCH_TIER_3_ROLE_ID)
        t3_subs = [t3_role_role, gifted_t3_role, twitch_t3]

        na_inhouses = self.client.get_channel(NA_OPEN_INHOUSE_CHANNEL_ID)
        eu_inhouses = self.client.get_channel(EU_OPEN_INHOUSE_CHANNEL_ID)

        for t3 in t3_subs:
            await na_inhouses.set_permissions(t3, view_channel=na_queues_open)
            await eu_inhouses.set_permissions(t3, view_channel=eu_queues_open)

    @tasks.loop(minutes=1.0)
    async def send_count(self):
        guild = await self.client.fetch_guild(GUILD_ID)
        guild_members = guild.fetch_members(limit=None)

        premium_id_count = {premium_id: 0 for premium_id in PREMIUM_IDS}
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
    try:
        response = requests.post(
            url=PUBLISH_COUNT_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
        )
        if response.status_code != 200:
            LOG.error(f"Failed to publish sub count: {response.text}")
    except:
        LOG.error(f"Failed to publish sub count - an exception occurred")

from discord import Client, SelectOption, Interaction, TextStyle
from discord.ui import View, Select, TextInput, Modal
from controllers.point_history_controller import PointHistoryController

import requests
from threading import Thread
from util.server_utils import get_base_url
from db import DB
from db.models import ChannelReward
from config import YAMLConfig as Config
from models.transaction import Transaction
import logging

from .pending_reward_view import PendingRewardView

PUBLISH_URL = f"{get_base_url()}/publish-streamdeck"

AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]
STREAM_CHAT_ID = Config.CONFIG["Discord"]["Channels"]["Stream"]

LOG = logging.getLogger(__name__)


class RedeemTTSView(Modal, title="Redeem a TTS Message"):
    def __init__(
        self,
        user_points: int,
        voice_id: str,
        voice_name: str,
        cost: int,
        client: Client,
    ):
        super().__init__(timeout=None)

        self.cost = cost
        self.voice_id = voice_id
        self.voice_name = voice_name
        self.client = client
        self.user_points = user_points

        self.text = TextInput(
            label="TTS Message",
            placeholder="Hey Hooj, love the content.",
            style=TextStyle.paragraph,
            required=True,
            min_length=1,
            max_length=200,
        )

        # self.select = Select(placeholder="Voice Selection", options=self.options)

        # self.add_item(self.select)
        self.add_item(self.text)

    async def on_submit(self, interaction: Interaction):
        if self.cost > 0:
            success, balance = DB().withdraw_points(interaction.user.id, self.cost)
            if not success:
                return await interaction.response.send_message(
                    "Failed to redeem reward - please try again.", ephemeral=True
                )

            PointHistoryController.record_transaction(
                Transaction(
                    interaction.user.id,
                    -self.cost,
                    self.user_points,
                    balance,
                    "TTS Redemption",
                )
            )
        else:
            balance = DB().get_point_balance(interaction.user.id)

        Thread(
            target=publish_tts,
            args=(
                self.voice_id,
                self.voice_name,
                self.text.value,
                interaction.user.display_name,
            ),
        ).start()

        await interaction.response.send_message(
            f"TTS Redeemed! You have {balance} points remaining after spending {self.cost}.",
            ephemeral=True,
        )


def publish_tts(voice_id: str, voice_name: str, message: str, sender_nickname: str):
    payload = {
        "type": "tts",
        "voice_id": voice_id,
        "voice_name": voice_name,
        "message": message,
        "sender_nickname": sender_nickname,
    }

    response = requests.post(
        url=PUBLISH_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish tts: {response.text}")

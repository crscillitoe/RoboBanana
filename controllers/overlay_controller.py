from threading import Thread
import requests

from util.server_utils import get_base_url
from config import YAMLConfig as Config
import logging

PUBLISH_OVERLAY_URL = f"{get_base_url()}/publish-overlay"
AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]

LOG = logging.getLogger(__name__)


class OverlayController:
    @staticmethod
    def publish_overlay(overlay_config: dict):
        Thread(
            target=publish_overlay,
            args=(overlay_config,),
        ).start()


def publish_overlay(overlay_config: dict):
    response = requests.patch(
        url=PUBLISH_OVERLAY_URL,
        json=overlay_config,
        headers={"x-access-token": AUTH_TOKEN},
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish overlay updates: {response.text}")

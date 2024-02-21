import asyncio
from quart_cors import cors
from server.blueprints.sse import sse
from server.blueprints.predictions import prediction_blueprint
from server.blueprints.timer import timer_blueprint
from server.blueprints.vod import vod_blueprint
from server.blueprints.chess import chess_blueprint
from server.blueprints.cool import cool_blueprint
from server.blueprints.poll import poll_blueprint
from server.blueprints.chat import chat_blueprint
from server.blueprints.streamdeck import streamdeck_blueprint
from server.blueprints.sub import sub_blueprint
from server.blueprints.tamagachi import tamagachi_blueprint
from server.blueprints.overlay import overlay_blueprint
from server.blueprints.connect_four import connect_four_blueprint
from server.blueprints.overlay_message import overlay_message_blueprint
from server.util.discord_client import DISCORD_CLIENT, start_discord_client
from server.util.keep_alive import start_keepalive
from server.blueprints.chat import publish_chat
from threading import Thread
from quart import Quart
from config import YAMLConfig as Config
from twitch_chat_irc import twitch_chat_irc
from util.server_utils import get_base_url

import requests
import discord
import logging

PUBLISH_URL = f"{get_base_url()}/publish-chat"

discord.utils.setup_logging(level=logging.INFO, root=True)

CACHE_HOST = Config.CONFIG["Server"]["Cache"]["Host"]
AUTH_TOKEN = Config.CONFIG["Secrets"]["Server"]["Token"]

app = Quart(__name__)
app = cors(app, allow_origin="*")
app.config["REDIS_URL"] = f"redis://{CACHE_HOST}"

app.register_blueprint(sse, url_prefix="/stream")
app.register_blueprint(prediction_blueprint)
app.register_blueprint(chess_blueprint)
app.register_blueprint(timer_blueprint)
app.register_blueprint(vod_blueprint)
app.register_blueprint(chat_blueprint)
app.register_blueprint(cool_blueprint)
app.register_blueprint(poll_blueprint)
app.register_blueprint(sub_blueprint)
app.register_blueprint(streamdeck_blueprint)
app.register_blueprint(tamagachi_blueprint)
app.register_blueprint(overlay_blueprint)
app.register_blueprint(connect_four_blueprint)
app.register_blueprint(overlay_message_blueprint)


LOG = logging.getLogger(__name__)


@app.before_serving
async def setup():
    Thread(target=async_setup()).start()
    Thread(target=start_listener).start()


def async_setup():
    start_keepalive(app)
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(start_discord_client(DISCORD_CLIENT), loop=loop)


@app.route("/")
async def index():
    return ("OK", 200)


def twitch_message_received(msg):
    logging.debug(msg)
    logging.debug(msg["color"])
    logging.debug(msg["display-name"])
    logging.debug(msg["message"])

    if msg["color"] != "":
        color = tuple(int(msg["color"].lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    else:
        color = (218, 165, 32)

    logging.debug(color)

    to_send = {
        "content": msg["message"],
        "displayName": msg["display-name"],
        "roles": [
            {
                "colorR": color[0],
                "colorG": color[1],
                "colorB": color[2],
                "icon": None,
                "id": 1,
                "name": "Twitch Chatter",
            }
        ],
        "stickers": [],
        "emojis": [],
        "mentions": [],
        "author_id": msg["user-id"],
        "platform": "twitch",
    }

    response = requests.post(
        url=PUBLISH_URL, json=to_send, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish chat: {response.text}")


def start_listener():
    twitch = twitch_chat_irc.TwitchChatIRC()
    twitch.listen("woohoojin", on_message=twitch_message_received)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)

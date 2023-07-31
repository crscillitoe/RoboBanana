import asyncio
from quart_cors import cors
from server.blueprints.sse import sse
from server.blueprints.predictions import prediction_blueprint
from server.blueprints.timer import timer_blueprint
from server.blueprints.vod import vod_blueprint
from server.blueprints.chess import chess_blueprint
from server.blueprints.cool import cool_blueprint
from server.blueprints.poll import poll_blueprint
from server.blueprints.sub import sub_blueprint
from server.blueprints.tamagachi import tamagachi_blueprint
from server.util.discord_client import DISCORD_CLIENT, start_discord_client
from server.util.keep_alive import start_keepalive
from threading import Thread
from quart import Quart

import discord
import logging

discord.utils.setup_logging(level=logging.INFO, root=True)

app = Quart(__name__)
app = cors(app, allow_origin="*")
app.config["REDIS_URL"] = "redis://localhost"

app.register_blueprint(sse, url_prefix="/stream")
app.register_blueprint(prediction_blueprint)
app.register_blueprint(chess_blueprint)
app.register_blueprint(timer_blueprint)
app.register_blueprint(vod_blueprint)
app.register_blueprint(cool_blueprint)
app.register_blueprint(poll_blueprint)
app.register_blueprint(sub_blueprint)
app.register_blueprint(tamagachi_blueprint)


LOG = logging.getLogger(__name__)


@app.before_serving
async def setup():
    Thread(target=async_setup()).start()


def async_setup():
    start_keepalive(app)
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(start_discord_client(DISCORD_CLIENT), loop=loop)


@app.route("/")
async def index():
    return ("OK", 200)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)

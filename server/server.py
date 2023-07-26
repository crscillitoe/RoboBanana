import quart.flask_patch
import asyncio
from quart_cors import cors
from db.models import PredictionChoice
from server.blueprints.sse_blueprint import sse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import Config
from server.controllers.prediction_controller import PredictionController
from server.models.quick_prediction import QuickPrediction
from server.token_required import token_required
from discord import Client, Intents
from threading import Thread
from quart import Quart, request, jsonify

import discord
import logging

discord.utils.setup_logging(level=logging.INFO, root=True)
logging.getLogger("apscheduler.executors.default").setLevel(logging.ERROR)

app = Quart(__name__)
app.config["REDIS_URL"] = "redis://localhost"
app.register_blueprint(sse, url_prefix="/stream")

cors(app, allow_origin="*")

last_published = {}
PREDICTIONS_CHANNEL = "predictions"
SUBS_CHANNEL = "subs"
SUBS_COUNT_CHANNEL = "subs-count"

# User responses to current active poll
POLL_ANSWERS_CHANNEL = "poll-answers"

# New poll information
POLLS_CHANNEL = "polls"

# Track the cool level of current VOD
COOL_CHANNEL = "cool"

VOD_REVIEW_CHANNEL = "vod-reviews"

TIMER_CHANNEL = "timer"

TAMAGACHI_CHANNEL = "tamagachi"

LOG = logging.getLogger(__name__)


async def keep_alive():
    async with app.app_context():
        sse.publish("\n\n", type="keepalive", channel=PREDICTIONS_CHANNEL)
        sse.publish("\n\n", type="keepalive", channel=SUBS_CHANNEL)
        sse.publish("\n\n", type="keepalive", channel=POLL_ANSWERS_CHANNEL)
        sse.publish("\n\n", type="keepalive", channel=POLLS_CHANNEL)
        sse.publish("\n\n", type="keepalive", channel=COOL_CHANNEL)
        sse.publish("\n\n", type="keepalive", channel=SUBS_COUNT_CHANNEL)
        sse.publish("\n\n", type="keepalive", channel=TIMER_CHANNEL)
        sse.publish("\n\n", type="keepalive", channel=VOD_REVIEW_CHANNEL)
        sse.publish("\n\n", type="keepalive", channel=TAMAGACHI_CHANNEL)


sched = AsyncIOScheduler()
sched.add_job(keep_alive, "interval", seconds=15)
sched.start()


@app.before_serving
async def setup():
    Thread(target=start_stuff()).start()


def start_stuff():
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(main(), loop=loop)


@app.route("/")
async def index():
    return jsonify(last_published)


@app.route("/publish-tamagachi", methods=["POST"])
@token_required
async def publish_tamagachi():
    try:
        to_publish = await parse_tamagachi_from_request()
        sse.publish(to_publish, type="publish", channel=TAMAGACHI_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@app.route("/publish-timer", methods=["POST"])
@token_required
async def publish_timer():
    try:
        to_publish = await parse_timer_from_request()
        sse.publish(to_publish, type="publish", channel=TIMER_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@app.route("/publish-vod", methods=["POST"])
@token_required
async def publish_vod():
    try:
        to_publish = await parse_vod_from_request()
        sse.publish(to_publish, type="publish", channel=VOD_REVIEW_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@app.route("/publish-cool", methods=["POST"])
@token_required
async def publish_cool():
    try:
        to_publish = await parse_cool_from_request()
        sse.publish(to_publish, type="publish", channel=COOL_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@app.route("/publish-poll", methods=["POST"])
@token_required
async def publish_poll():
    try:
        to_publish = await parse_poll_from_request()
        sse.publish(to_publish, type="publish", channel=POLLS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@app.route("/publish-poll-answer", methods=["POST"])
@token_required
async def publish_poll_answer():
    try:
        to_publish = await parse_poll_answer_from_request()
        sse.publish(to_publish, type="publish", channel=POLL_ANSWERS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@app.route("/publish-prediction", methods=["POST"])
@token_required
async def publish_prediction():
    global last_published
    try:
        to_publish = await parse_prediction_from_request()
        sse.publish(to_publish, type="publish", channel=PREDICTIONS_CHANNEL)
        last_published = to_publish
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@app.route("/publish-sub", methods=["POST"])
@token_required
async def publish_sub():
    try:
        to_publish = await parse_sub_from_request()
        sse.publish(to_publish, type="publish", channel=SUBS_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@app.route("/quick-prediction", methods=["POST"])
@token_required
async def quick_prediction():
    prediction_details = await parse_quick_prediction_from_request()
    status = await PredictionController.create_prediction(
        prediction_details, DISCORD_CLIENT
    )
    if not status:
        return ("Bad Request", 400)
    return ("OK", 200)


@app.route("/publish-sub-count", methods=["POST"])
@token_required
async def publish_sub_count():
    try:
        to_publish = await parse_sub_count_from_request()
        sse.publish(to_publish, type="publish", channel=SUBS_COUNT_CHANNEL)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@app.route("/close-prediction", methods=["GET"])
@token_required
async def close_prediction():
    await PredictionController.close_prediction()
    return ("OK", 200)


@app.route("/refund-prediction", methods=["GET"])
@token_required
async def refund_prediction():
    status = await PredictionController.refund_prediction(DISCORD_CLIENT)
    if not status:
        return ("Bad Request", 400)
    return ("OK", 200)


@app.route("/payout-prediction", methods=["POST"])
@token_required
async def payout_prediction():
    try:
        choice = await parse_payout_prediction_choice()
        await PredictionController.payout_prediction(choice, DISCORD_CLIENT)
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


async def parse_payout_prediction_choice():
    request_json = await request.get_json()
    choice = request_json["choice"]
    return PredictionChoice[choice]


async def parse_quick_prediction_from_request():
    request_json = await request.get_json()
    description = request_json["description"]
    option_one = request_json["optionOne"]
    option_two = request_json["optionTwo"]
    duration = int(request_json["duration"])

    return QuickPrediction(description, option_one, option_two, duration)


async def parse_prediction_from_request():
    request_json = await request.get_json()
    description = request_json["description"]
    option_one = request_json["optionOne"]
    option_two = request_json["optionTwo"]
    option_one_points = int(request_json["optionOnePoints"])
    option_two_points = int(request_json["optionTwoPoints"])
    end_time = request_json["endTime"]
    accepting_entries = request_json["acceptingEntries"]
    ended = request_json["ended"]

    return {
        "description": description,
        "optionOne": option_one,
        "optionTwo": option_two,
        "optionOnePoints": option_one_points,
        "optionTwoPoints": option_two_points,
        "endTime": end_time,
        "acceptingEntries": accepting_entries,
        "ended": ended,
    }


async def parse_sub_count_from_request():
    request_json = await request.get_json()
    tier_1_count = request_json["tier1Count"]
    tier_2_count = request_json["tier2Count"]
    tier_3_count = request_json["tier3Count"]

    return {
        "tier1Count": tier_1_count,
        "tier2Count": tier_2_count,
        "tier3Count": tier_3_count,
    }


async def parse_sub_from_request():
    request_json = await request.get_json()
    name = request_json["name"]
    tier = request_json["tier"]
    message = request_json["message"]
    return {"name": name, "tier": tier, "message": message}


async def parse_poll_from_request():
    """
    {
        "title": "This is a sample poll",
        "options": [
            "Sample text",
            "123",
            "another option",
            "these are options"
        ]
    }
    """
    request_json = await request.get_json()
    title = request_json["title"]
    options = request_json["options"]
    return {"title": title, "options": options}


async def parse_vod_from_request():
    """
    {
        complete: true | false,
        username: string,
        rank: string,
        riotid: string
    }
    """
    request_json = await request.get_json()
    rank = request_json["rank"]
    riotid = request_json["riotid"]
    complete = request_json["complete"]
    username = request_json["username"]
    return {"complete": complete, "username": username, "rank": rank, "riotid": riotid}


async def parse_cool_from_request():
    """
    {
        cool: -1 | 1,
    }
    """
    request_json = await request.get_json()
    cool = request_json["cool"]
    return {"cool": cool}


async def parse_poll_answer_from_request():
    """
    Option Number is 1-indexed
    {
        "userID": 12938123,
        "optionNumber": 1,
        "userRoleIDs": [123, 823, 231, 293]
    }
    """
    request_json = await request.get_json()
    user_id = request_json["userID"]
    option_number = request_json["optionNumber"]
    user_roles = request_json["userRoleIDs"]
    return {"userID": user_id, "optionNumber": option_number, "userRoleIDs": user_roles}


async def parse_timer_from_request():
    """
    {
        // Seconds
        "time": 50,
        // Timer Direction
        "direction": "inc",
    }
    """
    request_json = await request.get_json()
    time = request_json["time"]
    direction = request_json["direction"]
    return {"time": time, "direction": direction}


async def parse_tamagachi_from_request():
    """
    {
        "feederName": "Woohoojin",
        "numFed": 10,
        "fruit": "Watermelon"
    }
    """
    request_json = await request.get_json()
    feeder_name = request_json["feederName"]
    num_fed = request_json["numFed"]
    fruit = request_json["fruit"]
    return {"feederName": feeder_name, "numFed": num_fed, "fruit": fruit}


class ServerBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True

        super().__init__(intents=intents)

    async def on_ready(self):
        LOG.info(f"Logged in as {self.user} (ID: {self.user.id})")


async def main():
    async with DISCORD_CLIENT:
        await DISCORD_CLIENT.start(Config.CONFIG["Discord"]["Token"])


DISCORD_CLIENT = ServerBot()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)

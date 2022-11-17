from flask import Flask, request, jsonify
from flask_cors import CORS
from blueprints.sse_blueprint import sse
from apscheduler.schedulers.background import BackgroundScheduler
from token_required import token_required

import discord
import logging

discord.utils.setup_logging(level=logging.INFO, root=True)
logging.getLogger("apscheduler.executors.default").setLevel(logging.ERROR)

app = Flask(__name__)
app.config["REDIS_URL"] = "redis://localhost"
app.register_blueprint(sse, url_prefix="/stream")

CORS(app, resources={"/stream": {"origins": "*"}})

last_published = {}


def keep_alive():
    with app.app_context():
        sse.publish("\n\n", type="keepalive")


sched = BackgroundScheduler(daemon=True)
sched.add_job(keep_alive, "interval", seconds=50)
sched.start()


@app.route("/")
def index():
    return jsonify(last_published)


@app.route("/publish-prediction", methods=["POST"])
@token_required
def publish_prediction():
    global last_published
    try:
        to_publish = parse_prediction_from_request()
        sse.publish(to_publish, type="publish", channel="predictions")
        last_published = to_publish
        logging.info(f"Published new data: {to_publish}")
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


@app.route("/publish-sub", methods=["POST"])
@token_required
def publish_sub():
    global last_published
    try:
        to_publish = parse_sub_from_request()
        sse.publish(to_publish, type="publish", channel="subs")
        logging.info(f"Published new data: {to_publish}")
        return ("OK", 200)
    except (KeyError, ValueError):
        return ("Bad Request", 400)


def parse_prediction_from_request():
    logging.info(request.json)
    description = request.json["description"]
    option_one = request.json["optionOne"]
    option_two = request.json["optionTwo"]
    option_one_points = int(request.json["optionOnePoints"])
    option_two_points = int(request.json["optionTwoPoints"])
    end_time = request.json["endTime"]
    accepting_entries = request.json["acceptingEntries"]
    return {
        "description": description,
        "optionOne": option_one,
        "optionTwo": option_two,
        "optionOnePoints": option_one_points,
        "optionTwoPoints": option_two_points,
        "endTime": end_time,
        "acceptingEntries": accepting_entries,
    }


def parse_sub_from_request():
    name = request.json["name"]
    tier = request.json["tier"]
    return {"name": name, "tier": tier}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)

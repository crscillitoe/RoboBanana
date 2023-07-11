from datetime import timezone
from typing import Optional
from discord import Client
import requests
from config import Config
from db.models import PredictionSummary
from threading import Thread
from db import DB
import logging

PUBLISH_URL = "http://localhost:3000/publish-prediction"
AUTH_TOKEN = Config.CONFIG["Server"]["AuthToken"]
LOG = logging.getLogger(__name__)


class UpdatePredictionController:
    def publish_prediction_summary(prediction_id: int):
        prediction_summary = DB().get_prediction_summary(prediction_id)
        Thread(
            target=UpdatePredictionController.publish_update, args=(prediction_summary,)
        ).start()

    def publish_prediction_end_summary(
        prediction_id: int, prediction_summary: Optional[PredictionSummary] = None
    ):
        if prediction_summary is None:
            prediction_summary = DB().get_prediction_summary(prediction_id)
        prediction_summary.ended = True
        Thread(
            target=UpdatePredictionController.publish_update, args=(prediction_summary,)
        ).start()

    @staticmethod
    def publish_update(prediction_summary: PredictionSummary):
        payload = {
            "description": prediction_summary.description,
            "optionOne": prediction_summary.option_one,
            "optionTwo": prediction_summary.option_two,
            "optionOnePoints": prediction_summary.option_one_points,
            "optionTwoPoints": prediction_summary.option_two_points,
            "endTime": prediction_summary.end_time.astimezone(timezone.utc).isoformat(),
            "acceptingEntries": prediction_summary.accepting_entries,
            "ended": prediction_summary.ended,
        }
        response = requests.post(
            url=PUBLISH_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
        )
        if response.status_code != 200:
            LOG.error(f"Failed to publish updated prediction summary: {response.text}")

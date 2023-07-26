from controllers.predictions.update_prediction_controller import (
    UpdatePredictionController,
)
from db import DB


class ClosePredictionController:
    @staticmethod
    async def close_prediction(guild_id: int):
        DB().close_prediction(guild_id)
        prediction_id = DB().get_ongoing_prediction_id(guild_id)
        UpdatePredictionController.publish_prediction_summary(prediction_id)

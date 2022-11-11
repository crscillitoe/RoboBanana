from datetime import datetime
from discord import Embed


class ClosePredictionEmbed(Embed):
    def __init__(
        self,
        description: str,
        end_time: datetime,
    ):
        super().__init__(
            title="Close Prediction!",
            description=description,
        )
        self.end_time = int(end_time.timestamp())
        self.add_field(
            name="Prediction End", value=f"<t:{self.end_time}:R>", inline=True
        )

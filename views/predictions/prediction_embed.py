from discord import Embed
from datetime import datetime
from db import DB


class PredictionEmbed(Embed):
    def __init__(
        self,
        guild_id: int,
        description: str,
        end_time: datetime,
    ):
        super().__init__(
            title="Prediction!",
            description=description,
        )

        self.guild_id = guild_id
        self.end_time = int(end_time.timestamp())

        self.update_fields()

    def update_fields(self) -> None:
        self.clear_fields()
        self.add_field(
            name="Prediction End", value=f"<t:{self.end_time}:R>", inline=True
        )

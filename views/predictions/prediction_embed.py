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
        option_one_points, option_two_points = DB().get_prediction_point_counts(
            self.guild_id
        )
        total_points = option_one_points + option_two_points
        if total_points == 0:
            total_points = 1

        option_one_percent = round((option_one_points / total_points) * 100, 1)
        option_two_percent = 100 - option_one_percent

        self.add_field(
            name="Option One Points",
            value=f"{option_one_points} ({option_one_percent}%)",
            inline=True,
        )
        self.add_field(
            name="Option Two Points",
            value=f"{option_two_points} ({option_two_percent}%)",
            inline=True,
        )

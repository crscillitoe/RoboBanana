from discord import Interaction
from db import DB
import pytz


class AimlabsTrackingController:
    async def register_user(aimlabs_id: str, timezone: str, interaction: Interaction):
        if timezone not in pytz.all_timezones_set:
            return await interaction.response.send_message(
                (
                    "Invalid timezone provided - please view valid timezones via"
                    " `/aimlabs timezones`"
                ),
                ephemeral=True,
            )
        DB().register_user(interaction.user.id, aimlabs_id, timezone)

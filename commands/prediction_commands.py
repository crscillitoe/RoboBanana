from typing import Optional
from discord import (
    AllowedMentions,
    app_commands,
    Interaction,
    Client,
)
from controllers.predictions.close_prediction_controller import (
    ClosePredictionController,
)
from controllers.predictions.payout_prediction_controller import (
    PayoutPredictionController,
)
from db import DB
from discord.app_commands.errors import AppCommandError, CheckFailure
from db.models import PredictionChoice, PredictionOutcome
from views.predictions.create_predictions_modal import CreatePredictionModal
from config import YAMLConfig as Config
import logging

LOG = logging.getLogger(__name__)
JOEL_DISCORD_ID = 112386674155122688
HOOJ_DISCORD_ID = 82969926125490176
PREDICTION_AUDIT_CHANNEL = Config.CONFIG["Discord"]["Predictions"]["AuditChannel"]
TIER3_ROLE_12MO = Config.CONFIG["Discord"]["Subscribers"]["12MonthTier3Role"]
TIER3_ROLE_18MO = Config.CONFIG["Discord"]["Subscribers"]["18MonthTier3Role"]
CHAT_MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["CMChatModerator"]
TRUSTWORTHY = Config.CONFIG["Discord"]["Roles"]["Trustworthy"]
MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]
# these are hardcoded until raze to radiant is over, or config file changes are allowed
# for testing on own setup, these need to be changed to your appropriate IDs
# HIDDEN_MOD_ROLE should be 1040337265790042172 when committing and refers to the Mod (Role Hidden)
# STAFF_DEVELOPER_ROLE should be 1226317841272279131 when committing and refers to the Staff Developer role
# PREDICTION_DEALER_ROLE should be 1229896209515282472 when committing and refers to the Dealer role for Predictions
HIDDEN_MOD_ROLE = 1040337265790042172
STAFF_DEVELOPER_ROLE = 1226317841272279131
PREDICTION_DEALER_ROLE = 1229896209515282472


@app_commands.guild_only()
class PredictionCommands(app_commands.Group, name="prediction"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    async def on_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, CheckFailure):
            return await interaction.response.send_message(
                "Failed to perform command - please verify permissions.", ephemeral=True
            )
        logging.error(error)
        return await super().on_error(interaction, error)

    @app_commands.command(name="start_prediction")
    @app_commands.checks.has_any_role(
        TIER3_ROLE_12MO,
        TIER3_ROLE_18MO,
        MOD_ROLE,
        HIDDEN_MOD_ROLE,
        CHAT_MOD_ROLE,
        STAFF_DEVELOPER_ROLE,
        TRUSTWORTHY,
        PREDICTION_DEALER_ROLE,
    )
    @app_commands.describe(
        set_nickname="Whether to prepend users names with their choice"
    )
    async def start_prediction(
        self, interaction: Interaction, set_nickname: Optional[bool] = False
    ):
        """Start new prediction"""
        if DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "There is already an ongoing prediction!", ephemeral=True
            )
        await interaction.response.send_modal(
            CreatePredictionModal(self.client, set_nickname)
        )

    @app_commands.command(name="refund_prediction")
    @app_commands.checks.has_any_role(
        MOD_ROLE, HIDDEN_MOD_ROLE, STAFF_DEVELOPER_ROLE, PREDICTION_DEALER_ROLE
    )
    async def refund_prediction(self, interaction: Interaction):
        """Refund ongoing prediction, giving users back the points they wagered"""
        await PayoutPredictionController.refund_prediction(interaction, self.client)

    @app_commands.command(name="close_prediction")
    @app_commands.checks.has_any_role(
        TIER3_ROLE_12MO,
        TIER3_ROLE_18MO,
        MOD_ROLE,
        HIDDEN_MOD_ROLE,
        CHAT_MOD_ROLE,
        STAFF_DEVELOPER_ROLE,
        TRUSTWORTHY,
        PREDICTION_DEALER_ROLE,
    )
    async def close_prediction(self, interaction: Interaction):
        """CLOSE PREDICTION"""
        if not DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "There is no open prediction!", ephemeral=True
            )

        await ClosePredictionController.close_prediction(interaction.guild_id)
        prediction_id = DB().get_ongoing_prediction_id(interaction.guild_id)
        prediction_message_id = DB().get_prediction_message_id(prediction_id)
        prediction_channel_id = DB().get_prediction_channel_id(prediction_id)
        prediction_message = await self.client.get_channel(
            prediction_channel_id
        ).fetch_message(prediction_message_id)

        audit_channel = interaction.guild.get_channel(PREDICTION_AUDIT_CHANNEL)
        await audit_channel.send(
            f"{interaction.user.mention} closed the current prediction.",
            allowed_mentions=AllowedMentions.none(),
        )

        await prediction_message.reply("Prediction closed!")
        await interaction.response.send_message("Prediction closed!", ephemeral=True)

    @app_commands.command(name="payout_prediction")
    @app_commands.checks.has_any_role(
        MOD_ROLE, HIDDEN_MOD_ROLE, STAFF_DEVELOPER_ROLE, PREDICTION_DEALER_ROLE
    )
    @app_commands.describe(option="Option to payout")
    async def payout_prediction(
        self, interaction: Interaction, option: PredictionChoice
    ):
        """Payout predicton to option left or right"""
        await PayoutPredictionController.payout_prediction(
            option, interaction, self.client
        )

    @app_commands.command(name="redo_payout")
    @app_commands.checks.has_any_role(
        MOD_ROLE, HIDDEN_MOD_ROLE, STAFF_DEVELOPER_ROLE, PREDICTION_DEALER_ROLE
    )
    @app_commands.describe(option="Option to payout")
    async def redo_payout(self, interaction: Interaction, option: PredictionOutcome):
        """Redo the last prediction's payout"""
        await PayoutPredictionController.redo_payout(option, interaction, self.client)

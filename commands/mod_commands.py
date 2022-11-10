from datetime import datetime
from discord import app_commands, Interaction, Client, User
from discord.app_commands.errors import AppCommandError, CheckFailure
from db import DB, RaffleType
from db.models import PredictionEntry
from views.predictions.create_predictions_modal import CreatePredictionModal
from views.raffle.new_raffle_modal import NewRaffleModal
from views.rewards.add_reward_modal import AddRewardModal
from controllers.raffle_controller import RaffleController


JOEL_DISCORD_ID = 112386674155122688
HOOJ_DISCORD_ID = 1037471015216885791


@app_commands.guild_only()
class ModCommands(app_commands.Group, name="mod"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @staticmethod
    def check_owner(interaction: Interaction) -> bool:
        return interaction.user.id == JOEL_DISCORD_ID

    @staticmethod
    def check_hooj(interaction: Interaction) -> bool:
        return interaction.user.id == HOOJ_DISCORD_ID

    async def on_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, CheckFailure):
            return await interaction.response.send_message(
                "Failed to perform command - please verify permissions.", ephemeral=True
            )
        super().on_error()

    @app_commands.command(name="sync")
    @app_commands.check(check_owner)
    @app_commands.checks.has_role("Mod")
    async def sync(self, interaction: Interaction) -> None:
        """Manually sync slash commands to guild"""

        guild = interaction.guild
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        await interaction.response.send_message("Commands synced", ephemeral=True)

    @app_commands.command(name="start")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(raffle_type="Raffle Type (default: normal)")
    async def start(
        self, interaction: Interaction, raffle_type: RaffleType = RaffleType.normal
    ):
        """Starts a new raffle"""

        if DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message(
                "There is already an ongoing raffle!"
            )
            return

        modal = NewRaffleModal(raffle_type=raffle_type)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="end")
    @app_commands.checks.has_role("Mod")
    async def end(
        self,
        interaction: Interaction,
        num_winners: int = 1,
    ) -> None:
        """Closes an existing raffle and pick the winner(s)"""

        if not DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message(
                "There is no ongoing raffle! You need to start a new one."
            )
            return

        raffle_message_id = DB().get_raffle_message_id(interaction.guild.id)
        if raffle_message_id is None:
            await interaction.response.send_message(
                "Oops! That raffle does not exist anymore."
            )
            return

        await RaffleController._end_raffle_impl(
            interaction, raffle_message_id, num_winners
        )
        DB().close_raffle(interaction.guild.id, end_time=datetime.now())

    @app_commands.command(name="add_reward")
    @app_commands.checks.has_role("Mod")
    async def add_reward(self, interaction: Interaction):
        """Creates new channel reward for redemption"""
        modal = AddRewardModal()
        await interaction.response.send_modal(modal)

    @app_commands.command(name="remove_reward")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(name="Name of reward to remove")
    async def remove_reward(self, interaction: Interaction, name: str):
        """Removes channel reward for redemption"""
        DB().remove_channel_reward(name)
        await interaction.response.send_message(
            f"Successfully removed {name}!", ephemeral=True
        )

    @app_commands.command(name="allow_redemptions")
    @app_commands.checks.has_role("Mod")
    async def allow_redemptions(self, interaction: Interaction):
        """Allow rewards to be redeemed"""
        DB().allow_redemptions()
        await interaction.response.send_message(
            "Redemptions are now enabled", ephemeral=True
        )

    @app_commands.command(name="pause_redemptions")
    @app_commands.checks.has_role("Mod")
    async def pause_redemptions(self, interaction: Interaction):
        """Pause rewards from being redeemed"""
        DB().pause_redemptions()
        await interaction.response.send_message(
            "Redemptions are now paused", ephemeral=True
        )

    @app_commands.command(name="check_redemption_status")
    @app_commands.checks.has_role("Mod")
    async def check_redemption_status(self, interaction: Interaction):
        """Check whether or not rewards are eligible to be redeemed"""
        status = DB().check_redemption_status()
        status_message = "allowed" if status else "paused"
        await interaction.response.send_message(
            f"Redemptions are currently {status_message}.", ephemeral=True
        )

    @app_commands.command(name="start_prediction")
    @app_commands.checks.has_role("Mod")
    async def start_prediction(self, interaction: Interaction):
        """Start new prediction"""
        if DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "There is already an ongoing prediction!", ephemeral=True
            )
        await interaction.response.send_modal(CreatePredictionModal())

    @app_commands.command(name="refund_prediction")
    @app_commands.checks.has_role("Mod")
    async def refund_prediction(self, interaction: Interaction):
        """Refund ongoing prediction, giving users back the points they wagered"""
        if not DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "No ongoing prediction!", ephemeral=True
            )

        if DB().accepting_prediction_entries(interaction.guild_id):
            return await interaction.response.send_message(
                "Please close prediction from entries before refunding!", ephemeral=True
            )

        option_one_entries = DB().get_prediction_entries_for_guess(
            interaction.guild_id, 0
        )

        option_two_entries = DB().get_prediction_entries_for_guess(
            interaction.guild_id, 1
        )

        entries = option_one_entries + option_two_entries
        for entry in entries:
            DB().deposit_points(entry.user_id, entry.channel_points)

        DB().complete_prediction(interaction.guild_id)
        await interaction.response.send_message(
            "Prediction has been refunded!", ephemeral=True
        )

    @app_commands.command(name="payout_prediction")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(option="Option to payout")
    async def payout_prediction(self, interaction: Interaction, option: int):
        """Payout predicton to option 0 or 1"""
        if not DB().has_ongoing_prediction(interaction.guild_id):
            return await interaction.response.send_message(
                "No ongoing prediction!", ephemeral=True
            )

        if DB().accepting_prediction_entries(interaction.guild_id):
            return await interaction.response.send_message(
                "Please close prediction from entries before paying out!",
                ephemeral=True,
            )

        option_one, option_two = DB().get_prediction_point_counts(interaction.guild_id)
        total_points = option_one + option_two
        winning_pot = option_one if option == 0 else option_two
        entries: list[PredictionEntry] = DB().get_prediction_entries_for_guess(
            interaction.guild_id, option
        )

        for entry in entries:
            pot_percentage = entry.channel_points / winning_pot
            payout = round(total_points * pot_percentage)
            DB().deposit_points(entry.user_id, payout)

        DB().complete_prediction(interaction.guild_id)
        await interaction.response.send_message(
            f"Payout complete! {total_points} distributed.", ephemeral=True
        )

    @app_commands.command(name="give_points")
    @app_commands.check(check_hooj)
    @app_commands.describe(user="User ID to award points")
    @app_commands.describe(points="Number of points to award")
    async def give_points(self, interaction: Interaction, user: User, points: int):
        """Manually give points to user"""
        success, _ = DB().deposit_points(user.id, points)
        if not success:
            return await interaction.response.send_message(
                f"Failed to award points - please try again.", ephemeral=True
            )
        await interaction.response.send_message(
            "Successfully awarded points!", ephemeral=True
        )

from discord import app_commands, Interaction, User, Client
from controllers.good_morning_controller import GoodMorningController
from controllers.prediction_controller import PredictionController
from db import DB
from db.models import PredictionChoice
from views.rewards.redeem_reward_view import RedeemRewardView


@app_commands.guild_only()
class ViewerCommands(app_commands.Group, name="hooj"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @app_commands.command(name="redeem")
    async def redeem_reward(self, interaction: Interaction):
        """Redeem an available channel reward"""
        redemptions_allowed = DB().check_redemption_status()
        if not redemptions_allowed:
            return await interaction.response.send_message(
                "Sorry! Reward redemptions are currently paused. Try again during stream!",
                ephemeral=True,
            )

        rewards = DB().get_channel_rewards()
        user_points = DB().get_point_balance(interaction.user.id)
        view = RedeemRewardView(user_points, rewards, self.client)
        await interaction.response.send_message(
            f"You currently have {user_points} points", view=view, ephemeral=True
        )

    @app_commands.command(name="list_rewards")
    async def list_rewards(self, interaction: Interaction):
        """List all available channel rewards"""
        rewards = DB().get_channel_rewards()
        return_message = "The rewards currently available to redeem are:\n\n"
        for reward in rewards:
            return_message += f"({reward.point_cost}) {reward.name}\n"
        await interaction.response.send_message(return_message, ephemeral=True)

    @app_commands.command(name="point_balance")
    async def point_balance(self, interaction: Interaction):
        """Get your current number of channel points"""
        user_points = DB().get_point_balance(interaction.user.id)
        await interaction.response.send_message(
            f"You currently have {user_points} points", ephemeral=True
        )

    @app_commands.command(name="bet")
    @app_commands.describe(choice="Choice to bet points on")
    @app_commands.describe(points="Number of channel points to bet")
    async def bet(
        self, interaction: Interaction, choice: PredictionChoice, points: int
    ):
        """Place bet on currently ongoing prediction"""
        success = await PredictionController.create_prediction_entry(
            points, choice, interaction, self.client
        )

        if not success:
            return

        await interaction.response.send_message(
            f"Vote cast with {points} points!", ephemeral=True
        )

    @app_commands.command(name="good_morning")
    async def good_morning(self, interaction: Interaction):
        """Say good morning! Check #good-morning-faq for details"""
        await GoodMorningController.accrue_good_morning(interaction)

    @app_commands.command(name="good_morning_points")
    async def good_morning_points(self, interaction: Interaction):
        """Check your current good morning points! Check #good-morning-faq for details"""
        await GoodMorningController.get_morning_points(interaction)

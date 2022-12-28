from db.models import ChannelPoints
from db.models import Users, TempRoles, TempRoleManagement
from sqlalchemy import select, update, insert
from sqlalchemy.orm import sessionmaker
from datetime import timedelta, datetime
from config import Config
from discord import Role
from datetime import datetime
from discord import app_commands, Interaction, Client, User
from discord.app_commands.errors import AppCommandError, CheckFailure
from controllers.prediction_controller import PredictionController
from db import DB, RaffleType
from db.models import Users, TempRoleManagement, TempRoles
from views.predictions.create_predictions_modal import CreatePredictionModal
from views.raffle.new_raffle_modal import NewRaffleModal
from views.rewards.add_reward_modal import AddRewardModal
from controllers.raffle_controller import RaffleController
from config import Config
import logging
import random


class RoleController:
    async def add_temp_role_discord(user_id: int, temp_role_id: int, interaction: Interaction) -> int:
        target_member = interaction.guild.get_member(user_id)
        target_member.add_roles(temp_role_id, atomic=False)





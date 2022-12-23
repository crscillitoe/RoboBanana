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
from db.models import PredictionChoice
from views.predictions.create_predictions_modal import CreatePredictionModal
from views.raffle.new_raffle_modal import NewRaffleModal
from views.rewards.add_reward_modal import AddRewardModal
from controllers.raffle_controller import RaffleController
from config import Config
import logging
import random


import discord

MIN_ACCRUAL_TIME = timedelta(minutes=15)
MAX_ACCRUAL_WINDOW = timedelta(minutes=30)
POINTS_PER_ACCRUAL = 50

ROLE_MULTIPLIERS: dict[str, int] = {
    int(Config.CONFIG["Discord"]["Tier1RoleID"]): 2,
    int(Config.CONFIG["Discord"]["GiftedTier1RoleID"]): 2,
    int(Config.CONFIG["Discord"]["Tier2RoleID"]): 3,
    int(Config.CONFIG["Discord"]["GiftedTier2RoleID"]): 3,
    int(Config.CONFIG["Discord"]["Tier3RoleID"]): 4,
    int(Config.CONFIG["Discord"]["GiftedTier3RoleID"]): 4,
}


def add_temp_role(user_id: int, temp_role_id: int, temp_role_duration: str, session: sessionmaker, roles: list[Role]) -> int:
    with session() as sess:
        result = sess.execute(
            select(TempRoleManagement).where(TempRoleManagement.user_id == user_id and TempRoles.temp_role_id == temp_role_id)
        ).first()
        if result is None:
            temp_role_expiration = datetime.now() + datetime.strptime(temp_role_duration, '%H')
            sess.execute(
                insert(TempRoleManagement).values(user_id=user_id, temp_role_id=temp_role_id, temp_role_expiration=temp_role_expiration)
            )
            return True




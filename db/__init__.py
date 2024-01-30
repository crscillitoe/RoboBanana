from datetime import datetime
from discord import Role
from sqlalchemy import create_engine, select, update, insert, func, DateTime
from sqlalchemy.orm import sessionmaker
from typing import Optional
from db.points_history import (
    delete_transactions,
    get_transaction_history,
    record_transaction,
)

from db.temproles import (
    delete_temprole,
    get_expired_roles,
    get_user_temproles,
    get_temprole_users,
    get_temprole_users_count,
    retrieve_temprole,
    set_temprole,
)
from db.vod_review_bank import (
    add_vod_review_balance,
    get_vod_review_balance,
    reset_vod_review_balance,
)
from models.transaction import Transaction

from .vod_submissions import (
    get_latest_timestamp,
    update_timestamp,
    reset_user,
)

from .point_accrual import (
    accrue_channel_points,
    deposit_points,
    get_point_balance,
    withdraw_points,
)
from .good_morning import (
    accrue_morning_points,
    get_morning_points,
    get_morning_reward_winners,
    get_today_morning_count,
    manual_increment_morning_points,
    reset_all_morning_points,
)
from .predictions import (
    accepting_prediction_entries,
    close_prediction,
    complete_prediction,
    create_prediction,
    create_prediction_entry,
    get_last_prediction,
    get_prediction_entries_for_guess,
    get_ongoing_prediction_id,
    get_prediction_point_counts,
    get_prediction_message_id,
    get_prediction_channel_id,
    get_prediction_summary,
    get_user_prediction_entry,
    has_ongoing_prediction,
    set_prediction_outcome,
)
from .channel_rewards import (
    add_channel_reward,
    get_channel_rewards,
    remove_channel_reward,
    allow_redemptions,
    pause_redemptions,
    check_redemption_status,
)
from .emoji_reactions import (
    get_reactions_for_user,
    toggle_emoji_reaction,
    get_emoji_reaction_delay,
    set_emoji_reaction_delay,
    get_emoji_reaction_last_used,
    set_emoji_reaction_last_used,
)
from .models import (
    Base,
    PointsHistory,
    Prediction,
    PredictionEntry,
    PredictionSummary,
    Raffle,
    RaffleEntry,
    RoleModifier,
    RaffleType,
    TempRoles,
    VodSubmission,
)
from config import YAMLConfig as Config


class DB:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(DB, cls).__new__(cls)
            cls.__instance.__initialized = False
        return cls.__instance

    def __init__(self):
        if self.__initialized:
            return

        self.__initialized = True

        username = Config.CONFIG["Database"]["Username"]
        password = Config.CONFIG["Secrets"]["Database"]["Password"]
        db_host = Config.CONFIG["Database"]["Host"]
        db_name = Config.CONFIG["Database"]["Name"]

        self.engine = create_engine(
            f"mysql+pymysql://{username}:{password}@{db_host}/{db_name}",
        )
        self.session = sessionmaker(self.engine, autoflush=True, autocommit=True)

        Base.metadata.create_all(self.engine)

    def create_raffle(
        self, guild_id: int, message_id: int, raffle_type: RaffleType
    ) -> None:
        if self.has_ongoing_raffle(guild_id):
            raise Exception("There is already an ongoing raffle!")

        with self.session() as sess:
            sess.execute(
                insert(Raffle).values(
                    guild_id=guild_id, message_id=message_id, raffle_type=raffle_type
                )
            )

    def create_raffle_entry(self, guild_id: int, user_id: int, tickets: int) -> None:
        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            sess.execute(
                insert(RaffleEntry).values(
                    raffle_id=raffle_id, user_id=user_id, tickets=tickets
                )
            )

    def get_user_raffle_entry(self, guild_id: int, user_id: int) -> RaffleEntry:
        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            stmt = (
                select(RaffleEntry)
                .where(RaffleEntry.raffle_id == raffle_id)
                .where(RaffleEntry.user_id == user_id)
            )
            result = sess.execute(stmt).all()

        if len(result) == 0:
            return None

        return result[0][0]

    def get_recent_win_stats(
        self, guild_id: int, user_id: int, after: datetime
    ) -> tuple[int, datetime]:
        """
        Query how many (normal) raffle wins a :user_id has had within a :guild_id since :after

        Returns wins since :after and the date they last won
        """
        with self.session() as sess:
            stmt = (
                select(func.count("*"), func.max(RaffleEntry.timestamp))
                .select_from(RaffleEntry)
                .join(Raffle)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == True)
                .where(Raffle.raffle_type == RaffleType.normal)
                .where(RaffleEntry.winner == True)
                .where(RaffleEntry.user_id == user_id)
                .where(Raffle.end_time > after)
            )

            result = sess.execute(stmt).one()

        return result

    def get_raffle_entries(self, guild_id: int) -> list[RaffleEntry]:
        if not self.has_ongoing_raffle(guild_id):
            return []

        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            stmt = (
                select(RaffleEntry)
                .join(Raffle)
                .where(Raffle.id == raffle_id)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == False)
                .where(RaffleEntry.winner == False)
            )
            result = sess.execute(stmt).all()

        return [r[0] for r in result]

    def get_loss_streak_for_user(self, user_id: int) -> int:
        """
        Fetch the current number of consecutive losses since the last win
        """

        with self.session() as sess:
            # get the most recent raffle entry with MAX(id)
            subquery = (
                select(func.ifnull(func.max(RaffleEntry.id), 0).label("last_win_id"))
                .join(Raffle)
                .where(RaffleEntry.winner == True)
                .where(RaffleEntry.user_id == user_id)
                .where(Raffle.raffle_type == RaffleType.normal)
                .subquery()
            )

            # count all losses for the same user after the last winning entry
            stmt = (
                select(func.count("*"))
                .select_from(RaffleEntry)
                .join(Raffle)
                .where(RaffleEntry.id > subquery.c.last_win_id)
                .where(RaffleEntry.winner == False)
                .where(RaffleEntry.user_id == user_id)
                .where(Raffle.raffle_type == RaffleType.normal)
            )
            result = sess.execute(stmt).one()

        return result[0]

    def get_raffle_entry_count(self, guild_id: int) -> int:
        # special case for immediately after raffle is created
        if not self.has_ongoing_raffle(guild_id):
            return 0

        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            stmt = (
                select(func.count("*"))
                .select_from(RaffleEntry)
                .where(RaffleEntry.raffle_id == raffle_id)
            )
            result = sess.execute(stmt).one()

        return result[0]

    def has_ongoing_raffle(self, guild_id: int) -> bool:
        with self.session() as sess:
            stmt = (
                select(Raffle)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == False)
            )
            result = sess.execute(stmt).all()

        return len(result) > 0

    def get_raffle_message_id(self, guild_id: int) -> Optional[int]:
        if not self.has_ongoing_raffle(guild_id):
            raise Exception("There is no ongoing raffle! You need to start a new one.")

        with self.session() as sess:
            stmt = (
                select(Raffle.message_id)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == False)
                .limit(1)
            )
            result = sess.execute(stmt).one()

        if len(result) == 0:
            return None

        return result[0]

    def get_raffle_id(self, guild_id: int) -> Optional[int]:
        if not self.has_ongoing_raffle(guild_id):
            raise Exception("There is no ongoing raffle! You need to start a new one.")

        with self.session() as sess:
            stmt = (
                select(Raffle.id)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == False)
                .limit(1)
            )
            result = sess.execute(stmt).one()

        if len(result) == 0:
            return None

        return result[0]

    def close_raffle(self, guild_id: int, end_time: datetime) -> None:
        if not self.has_ongoing_raffle(guild_id):
            raise Exception("There is no ongoing raffle! You need to start a new one.")

        with self.session() as sess:
            sess.execute(
                update(Raffle)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == False)
                .values(ended=True, end_time=end_time)
                .execution_options(synchronize_session="fetch")
            )

    def record_win(self, guild_id: int, user_ids: list[int]) -> None:
        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            # for uid in user_ids:
            sess.execute(
                update(RaffleEntry)
                .where(RaffleEntry.raffle_id == raffle_id)
                .where(RaffleEntry.user_id.in_(user_ids))
                .values(winner=True)
                .execution_options(synchronize_session=False)
            )

    def clear_win(self, raffle_message_id: int) -> None:
        with self.session() as sess:
            # TODO: do we want to enable this?
            # clear winner status from previous entries, so anyone can win again
            # sess.execute(
            #     update(RaffleEntry)
            #     .values(winner=False)
            #     .where(RaffleEntry.raffle_id == Raffle.id)
            #     .where(Raffle.message_id == raffle_message_id)
            #     .where(Raffle.ended == True)
            #     .execution_options(synchronize_session="fetch")
            # )
            sess.execute(
                update(Raffle)
                .values(ended=False, end_time=None)
                .where(Raffle.message_id == raffle_message_id)
                .where(Raffle.ended == True)
                .execution_options(synchronize_session="fetch")
            )

    def remove_raffle_winner(
        self, guild_id: int, user_id: int, after: datetime
    ) -> None:
        with self.session() as sess:
            # removes winner from raffle entry within last week, so winner can win again

            stmt = (
                select(Raffle.id)
                .select_from(RaffleEntry)
                .join(Raffle)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == True)
                .where(Raffle.raffle_type == RaffleType.normal)
                .where(RaffleEntry.winner == True)
                .where(RaffleEntry.user_id == user_id)
                .where(Raffle.end_time > after)
                .order_by(Raffle.id.desc())
                .limit(1)
            )

            last_win_raffle_id = sess.execute(stmt).scalar()

            if last_win_raffle_id is None:
                return False

            sess.execute(
                update(RaffleEntry)
                .values(winner=False)
                .where(RaffleEntry.user_id == user_id)
                .where(RaffleEntry.raffle_id == last_win_raffle_id)
                .where(RaffleEntry.winner == True)
                .execution_options(synchronize_session="fetch")
            )

            return True

    def get_role_modifiers(self, guild_id: int) -> dict[int, int]:
        with self.session() as sess:
            stmt = select(RoleModifier).where(RoleModifier.guild_id == guild_id)
            result = sess.execute(stmt).all()

        return {r[0].role_id: r[0].modifier for r in result}

    def accrue_channel_points(self, user_id: int, roles: list[Role]) -> bool:
        """Accrues channel points for a given user

        Args:
            user_id (int): Discord user ID to give points to
            roles (list[int]): List of Discord Role IDs that user is assigned

        Returns:
            bool: True if points were awarded to the user
        """
        return accrue_channel_points(user_id, roles, self.session)

    def accrue_morning_points(self, user_id: int) -> bool:
        """Accrues morning greeting points for a given user

        Args:
            user_id (int): Discord user ID to give points to
            session (sessionmaker): Open DB session

        Returns:
            bool: True if points were awarded to the user
        """
        return accrue_morning_points(user_id, self.session)

    def get_morning_points(self, user_id: int) -> int:
        """Get the number of morning greetings a user has accrued

        Args:
            user_id (int): Discord user ID to give a morning greeting to
            session (sessionmaker): Open DB session

        Returns:
            int: Number of morning greetings currently awarded
        """
        return get_morning_points(user_id, self.session)

    def get_today_morning_count(self) -> int:
        """Get the number of users which have said good morning today

        Returns:
            int: Number of users who have said good morning today
        """
        return get_today_morning_count(self.session)

    def get_morning_reward_winners(self) -> list[int]:
        """Get the Discord User IDs of all users who earned good morning reward

        Returns:
            list[int]: Discord User IDs of users to reward
        """
        return get_morning_reward_winners(self.session)

    def reset_all_morning_points(self):
        """Set weekly_count to 0 for all users"""
        return reset_all_morning_points(self.session)

    def manual_increment_morning_points(self, value: int):
        """Manually increment ALL USERS' morning points totals

        Args:
            value (int): Amount to increment users' morning points total by
        """
        return manual_increment_morning_points(value, self.session)

    def get_point_balance(self, user_id: int) -> int:
        """Get the number of points a user has accrued

        Args:
            user_id (int): Discord user ID to give points to

        Returns:
            int: Number of points currently accrued
        """
        return get_point_balance(user_id, self.session)

    def withdraw_points(self, user_id: int, point_amount: int) -> tuple[bool, int]:
        """Withdraw points from user's current balance

        Args:
            user_id (int): Discord user ID to give points to
            point_amount (int): Number of points to withdraw
            session (sessionmaker): Open DB session

        Returns:
            tuple[bool, int]: True if points were successfully withdrawn. If so, return new balance
        """
        return withdraw_points(user_id, point_amount, self.session)

    def deposit_points(self, user_id: int, point_amount: int) -> tuple[bool, int]:
        """Deposit points into user's current balance

        Args:
            user_id (int): Discord user ID to give points to
            point_amount (int): Number of points to withdraw
            session (sessionmaker): Open DB session

        Returns:
            tuple[bool, int]: True if points were successfully deposited. If so, return new balance
        """
        return deposit_points(user_id, point_amount, self.session)

    def add_channel_reward(self, name: str, point_cost: int):
        """Add new reward that can be redeemed for ChannelPoints

        Args:
            name (str): Name of channel reward
            point_cost (int): Number of ChannelPoints required to redeem
        """
        return add_channel_reward(name, point_cost, self.session)

    def remove_channel_reward(self, name: str):
        """Delete channel reward with matching name

        Args:
            name (str): Name of channel reward to delete
        """
        return remove_channel_reward(name, self.session)

    def get_channel_rewards(self):
        """Get all available channel rewards

        Returns:
            list[ChannelReward]: All currently available channel rewards
        """
        return get_channel_rewards(self.session)

    def allow_redemptions(self):
        """Allow channel rewards to be redeemed"""
        return allow_redemptions(self.session)

    def pause_redemptions(self):
        """Puase channel rewards from being redeemed"""
        return pause_redemptions(self.session)

    def check_redemption_status(self) -> bool:
        """Check whether or not channel rewards are eligible for redemption

        Returns:
            bool: True if rewards are currently allowed
        """
        return check_redemption_status(self.session)

    def create_prediction(
        self,
        guild_id: int,
        channel_id: int,
        message_id: str,
        description: str,
        option_one: str,
        option_two: str,
        end_time: datetime,
        set_nickname: bool,
    ):
        """Create new prediction for users to enter channel points into

        Args:
            guild_id (int): Discord Guild ID initiating prediction
            message_id (str): Discord ID for message initiating prediction
            description (str): Description of what viewers are trying to predict
            option_one (str): First option that users can vote for
            option_two (str): Second option that users can vote for
            end_time (datetime): Timestamp when prediction entries will no longer be accepted
        """
        return create_prediction(
            guild_id,
            channel_id,
            message_id,
            description,
            option_one,
            option_two,
            end_time,
            set_nickname,
            self.session,
        )

    def has_ongoing_prediction(self, guild_id: int) -> bool:
        """Check if the given Guild has an ongoing prediction

        Args:
            guild_id (int): Discord Guild ID which initiated prediction

        Returns:
            bool: True if there is an ongoing prediction
        """
        return has_ongoing_prediction(guild_id, self.session)

    def get_ongoing_prediction_id(self, guild_id: int) -> int:
        """Get ID for ongoing Prediction

        Args:
            guild_id (int): Discord Guild ID which initiated prediction

        Returns:
            int: ID of incomplete Prediction
        """
        return get_ongoing_prediction_id(guild_id, self.session)

    def get_prediction_point_counts(self, prediction_id: int) -> tuple[int, int]:
        """Get the total points predicted on each option

        Args:
            prediction_id (int): ID of Prediction to get point totals for

        Returns:
            tuple[int, int]: The total points voted for each option
        """
        return get_prediction_point_counts(prediction_id, self.session)

    def create_prediction_entry(
        self, guild_id: int, user_id: int, channel_points: int, guess: int
    ) -> bool:
        """Create new prediction entry for user

        Args:
            guild_id (int): Discord Guild ID which created prediction
            user_id (int): Discord ID of user voting
            channel_points (int): Number of channel points to vote
            guess (int): Option to vote for
        Returns:
            bool: True if prediction entry sucessfully created
        """
        return create_prediction_entry(
            guild_id, user_id, channel_points, guess, self.session
        )

    def get_prediction_message_id(self, prediction_id: int) -> Optional[int]:
        """Get message ID of initial prediction start

        Args:
            prediction_id (int): ID of Prediction to retrieve starting message for

        Returns:
            Optional(int): ID of message which started prediction
        """
        return get_prediction_message_id(prediction_id, self.session)

    def get_prediction_channel_id(self, prediction_id: int) -> Optional[int]:
        """Get channel ID of an ongoing prediction

        Args:
            prediction_id (int): ID of Prediction to retrieve channel for

        Returns:
            Optional(int): ID of channel that the prediction belongs to
        """
        return get_prediction_channel_id(prediction_id, self.session)

    def get_user_prediction_entry(self, guild_id: int, user_id: int):
        """Gets user prediction entry for given user id

        Args:
            guild_id (int): Discord Guild ID which initiated prediction
            user_id (int): Discord User ID to retrieve entry for

        Returns:
            Optional[PredictionEntry]: PredictionEntry for user if one has been cast
        """
        return get_user_prediction_entry(guild_id, user_id, self.session)

    def accepting_prediction_entries(self, guild_id: int) -> bool:
        """Check if current prediction is accepting entries

        Args:
            guild_id (int): Discord Guild ID which initiated prediction

        Returns:
            bool: True if entries are currently being accepted
        """

        return accepting_prediction_entries(guild_id, self.session)

    def close_prediction(self, guild_id: int):
        """Close prediction from currently accepting entries

        Args:
            guild_id (int): Discord Guild ID which initiated prediction
        """
        return close_prediction(guild_id, self.session)

    def complete_prediction(self, guild_id: int, winning_option: int):
        """Complete prediction, indicating points have been paid out

        Args:
            guild_id (int): Discord Guild ID which initiated prediction
            winning_option (int): Prediction option which was paid out
        """
        return complete_prediction(guild_id, winning_option, self.session)

    def get_prediction_entries_for_guess(
        self, prediction_id: int, guess: int
    ) -> list[PredictionEntry]:
        """Get all PredictionEntries that voted for an option

        Args:
            prediction_id (int): ID of Prediction to get entries for
            guess (int): Option to retrieve entries for
            prediction_id (Optional[int]): None to use ongoing prediction, otherwise specified ID

        Returns:
            list[PredictionEntry]: All entries cast for given option
        """
        return get_prediction_entries_for_guess(prediction_id, guess, self.session)

    def get_prediction_summary(self, prediction_id: int) -> PredictionSummary:
        """Get prediction sumamry for ongoing prediction

        Args:
            prediction_id (int): ID of Prediction to get summary for

        Returns:
            PredictionSummary: Summary about the current state of the ongoing prediction
        """
        return get_prediction_summary(prediction_id, self.session)

    def get_last_prediction(self, guild_id: int) -> Prediction:
        """Gets the last prediction run for a guild

        Args:
            guild_id (int): Discord Guild ID which initiated prediction

        Returns:
            Prediction: The Prediction which was last run
        """
        return get_last_prediction(guild_id, self.session)

    def set_prediction_outcome(self, prediction_id: int, winning_outcome: int):
        """Sets winning_option of prediction to the specified outcome

        Args:
            prediction_id (int): ID of prediction to alter outcome for
            winning_outcome (int): New outcome of prediction
        """
        return set_prediction_outcome(prediction_id, winning_outcome, self.session)

    def get_latest_timestamp(self, user_id: int):
        return get_latest_timestamp(user_id, self.session)

    def update_timestamp(self, user_id: int):
        return update_timestamp(user_id, self.session)

    def reset_user(self, user_id: int):
        return reset_user(user_id, self.session)

    def toggle_emoji_reaction(self, user_id: int, emoji: str) -> bool:
        """Toggles emoji reaction for a given user

        Args:
            user_id (int): Discord User ID to add reaction to
            emoji (str): Discord \emoji_name representation of emoji to add to messages

        Returns:
            bool: True if emoji was toggled ON, False if toggled OFF
        """
        return toggle_emoji_reaction(user_id, emoji, self.session)

    def get_reactions_for_user(self, user_id: int) -> list[str]:
        """Get reactions to apply to a user's messages

        Args:
            user_id (int): Discord User ID to add reaction to

        Returns:
            list[str]: Emojis to apply to messages
        """
        return get_reactions_for_user(user_id, self.session)

    def get_emoji_reaction_delay(self):
        """Get Robomoji delay time

        Returns:
            int: Delay time in seconds for Robomojis
        """
        return get_emoji_reaction_delay(self.session)

    def set_emoji_reaction_delay(self, delay_time: int):
        """Set Robomoji delay time

        Args:
            delay_time (int): Delay time in seconds for Robomojis
        """
        return set_emoji_reaction_delay(delay_time, self.session)

    def get_emoji_reaction_last_used(
        self,
        user_id: int,
    ):
        """
        Get DateTime of last Robomoji reaction

        Args:
            user_id (int): Discord User ID to add reaction to

        Returns:
            DateTime: DateTime of last Robomoji reaction for given user
        """
        return get_emoji_reaction_last_used(user_id, self.session)

    def set_emoji_reaction_last_used(self, user_id: int, last_used: DateTime):
        """
        Set DateTime of last Robomoji reaction

        Args:
            user_id (int): Discord User ID to add reaction to
            last_used (DateTime):  DateTime of most recently used Robomoji reaction
        """
        return set_emoji_reaction_last_used(user_id, last_used, self.session)

    def set_temprole(
        self, user_id: int, role_id: int, guild_id: int, expiration: datetime
    ):
        """Set temprole for user to specified duration, even if one exists already

        Args:
            user_id (int): Discord User ID to grant role to
            role_id (int): Role ID to grant to user
            guild_id (int): Discord Guild ID the user belongs to
            expiration (datetime): Expiration date of role
        """
        return set_temprole(user_id, role_id, guild_id, expiration, self.session)

    def retrieve_temprole(self, user_id: int, role_id: int) -> TempRoles | None:
        """Retrieve temprole for user_id / role_id pairing

        Args:
            user_id (int): Discord User ID of user to grab temprole for
            role_id (int): Discord Role ID of role to grab temprole for

        Returns:
            TempRoles | None: None if no pairing exists, TempRoles otherwise
        """
        return retrieve_temprole(user_id, role_id, self.session)

    def get_expired_roles(self, compare_time: datetime) -> list[TempRoles]:
        """Get temproles which will expire by given time

        Args:
            compare_time (datetime): Time to compare temproles to
            session (sessionmaker): Open DB session

        Returns:
            list[TempRoles]: All temproles which will be expired by this time
        """
        return get_expired_roles(compare_time, self.session)

    def get_user_temproles(self, user_id: int, guild_id: int) -> list[TempRoles]:
        """Get all temproles assigned to user

        Args:
            user_id (int): Discord User ID to grab roles for
            guild_id (int): Guild ID to grab roles for

        Returns:
            list[TempRoles]: All temproles assigned to user
        """
        return get_user_temproles(user_id, guild_id, self.session)

    def get_temprole_users(
        self, role_id: int, guild_id: int, offset: int = 0, limit: int = None
    ) -> list[TempRoles]:
        """Get all users that have given temprole

        Args:
            role_id (int): Discord Role ID to grab users for
            guild_id (int): Guild ID to grab users for
            offset (int, optional): Number of results to skip. Default is 0
            limit (int): Max number of results to return. Default is all results

        Returns:
            list[TempRoles]: All users that have given temprole
        """
        return get_temprole_users(role_id, guild_id, self.session, offset, limit)

    def get_temprole_users_count(self, role_id: int, guild_id: int) -> int:
        """Get number of users that have given temprole

        Args:
            role_id (int): Discord Role ID to grab users for
            guild_id (int): Guild ID to grab users for

        Returns:
            int: Number of users that have given temprole
        """
        return get_temprole_users_count(role_id, guild_id, self.session)

    def delete_temprole(self, id: int):
        """Remove temprole from database with corresponding id

        Args:
            id (int): Temprole ID to delete
        """
        return delete_temprole(id, self.session)

    def add_vod_review_balance(self, user_id: int, amount: int):
        """Add VOD review balance for specified user

        Args:
            user_id (int): Discord User ID of user who performed review
        """
        return add_vod_review_balance(user_id, amount, self.session)

    def get_vod_review_balance(self, user_id: int) -> Optional[int]:
        """Get VOD review balance for specified user

        Args:
            user_id (int): Discord User ID
        """
        return get_vod_review_balance(user_id, self.session)

    def reset_vod_review_balance(self, user_id: int):
        """Reset VOD Review balance to 0h for specified user

        Args:
            user_id (int): Discord User ID of user to reset balance for
        """
        return reset_vod_review_balance(user_id, self.session)

    def record_transaction(self, transaction: Transaction):
        """Record transaction into points history respecting maximum
        maximum transaction limit

        Args:
            transaction (Transaction): Transaction data to record
        """
        return record_transaction(transaction, self.session)

    def get_transaction_history(self, user_id: int):
        """Get transaction history for user

        Args:
            user_id (int): Discord User ID of user

        Returns:
            list[PointsHistory]: Up to MAXIMUM_TRANSACTIONS most recent point transactions
        """
        return get_transaction_history(user_id, self.session)

    def delete_transactions(self, transactions: list[PointsHistory]):
        """Delete transactions from PointsHistory

        Args:
            transactions (list[PointsHistory]): Transactions to delete
            session (sessionmaker): Open DB session
        """
        return delete_transactions(transactions, self.session)

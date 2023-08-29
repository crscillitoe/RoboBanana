import discord
from datetime import datetime, timedelta
from typing import Optional
from discord import Interaction, Member, User
from db import DB, RaffleEntry, RaffleType
from config import YAMLConfig as Config
import random

VOD_APPROVED_ROLE_ID = Config.CONFIG["Discord"]["VODReview"]["ApprovedRole"]
VOD_SUBMISSION_CHANNEL_ID = Config.CONFIG["Discord"]["VODReview"]["SubmissionChannel"]


class RaffleController:
    @staticmethod
    async def _end_raffle_impl(
        interaction: Interaction,
        raffle_message_id: int,
        num_winners: int,
    ) -> None:
        if num_winners == 0:
            await interaction.response.send_message("There is no winner.")
            return

        guild_id = interaction.guild.id
        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        if raffle_message is None:
            raise Exception("Oops! That raffle does not exist anymore.")

        await interaction.response.defer(thinking=True)

        raffle_entries = DB().get_raffle_entries(guild_id)
        if len(raffle_entries) == 0:
            await interaction.followup.send("No one is elligible to win the raffle.")
            return

        winner_ids = RaffleController.choose_winners(raffle_entries, num_winners)
        winners = [interaction.guild.get_member(_id) for _id in winner_ids]

        if len(winners) == 1:
            await interaction.followup.send(f"{winners[0].mention} has won the raffle!")
        else:
            await interaction.followup.send(
                f"Raffle winners are: {', '.join(w.mention for w in winners)}!"
            )

        DB().record_win(guild_id, winner_ids)

    @staticmethod
    def choose_winners(entries: list[RaffleEntry], num_winners: int) -> list[int]:
        """
        Every raffle entry has a ticket count, which is their entry weight.

        Then we let random.choices work its magic.
        """
        if len(entries) < num_winners:
            raise Exception("There are not enough entries for that many winners.")

        # step 1. convert raffle entries into lists of user_ids and tickets
        entrants = []
        entrant_weights = []
        for ent in entries:
            entrants.append(ent.user_id)
            entrant_weights.append(ent.tickets)

        # step 3. using weighted probability (without replacement), select the random winner(s)
        winners = RaffleController.weighted_sample_without_replacement(
            population=entrants, weights=entrant_weights, k=num_winners
        )

        return winners

    # h/t https://maxhalford.github.io/blog/weighted-sampling-without-replacement/
    @staticmethod
    def weighted_sample_without_replacement(population, weights, k):
        v = [random.random() ** (1 / w) for w in weights]
        order = sorted(range(len(population)), key=lambda i: v[i])
        return [population[i] for i in order[-k:]]

    @staticmethod
    def get_tickets(guild_id: int, user: Member, raffle_type: RaffleType) -> int:
        """
        Calculate the number of tickers a specific user should have for a raffle entry.
        """
        # every entrant starts with 100 ticket
        tickets = 100

        # + any role modifiers from the DB
        role_modifiers = DB().get_role_modifiers(guild_id)
        tickets += sum(role_modifiers.get(r.id, 0) for r in user.roles)

        # add bad luck protection for normal raffles
        if raffle_type == RaffleType.normal:
            # + 5tk/loss since last win
            loss_streak = DB().get_loss_streak_for_user(user.id)
            tickets += 5 * loss_streak

        return tickets

    @staticmethod
    def eligible_for_raffle(guild_id: int, user: User) -> tuple[bool, Optional[str]]:
        vod_approved_role = discord.utils.get(user.roles, id=VOD_APPROVED_ROLE_ID)
        if vod_approved_role is None:
            return (
                False,
                (
                    f"VODs must be submitted to <#{VOD_SUBMISSION_CHANNEL_ID}> and"
                    " approved ahead of entering a raffle."
                ),
            )

        one_week_ago = datetime.now().date() - timedelta(days=6)
        weekly_wins, last_win_entry_dt = DB().get_recent_win_stats(
            guild_id=guild_id, user_id=user.id, after=one_week_ago
        )
        if weekly_wins > 0 and last_win_entry_dt is not None:
            next_eligible_date = last_win_entry_dt.date() + timedelta(days=7)
            next_eligible_ts = int(
                datetime.combine(next_eligible_date, datetime.min.time()).timestamp()
            )
            return (
                False,
                (
                    "You can only win the raffle once per week. You can next enter on"
                    f" <t:{next_eligible_ts}:D>"
                ),
            )
        return True, None

from discord import Embed
from datetime import datetime
from db import DB, RaffleType


class RaffleEmbed(Embed):
    def __init__(
        self,
        guild_id: int,
        description: str | None,
        end_time: datetime,
        role_odds: list[tuple[str, int]],
        raffle_type: RaffleType,
    ):
        super().__init__(
            title="VOD Review Raffle",
            description=description,
        )

        self.guild_id = guild_id
        self.raffle_type = raffle_type
        self.end_time = int(end_time.timestamp())

        # global odds
        global_odds_str_parts = ["Everyone: +100 Tickets"]
        if self.raffle_type == RaffleType.normal:
            global_odds_str_parts += [
                "Bad Luck Protection*: +5 Tickets",
                "",
                "*\*Per consecutive loss, resets when you win.*",
            ]
        self.global_odds_str = "\n".join(global_odds_str_parts)

        # role odds
        self.role_odds_str = "\n".join(
            f"{name}: {'+' if mod > 0 else '-'}{mod} Tickets" for name, mod in role_odds
        )

        self.update_fields()

    def update_fields(self) -> None:
        self.clear_fields()
        self.add_field(name="Raffle End", value=f"<t:{self.end_time}:R>", inline=True)
        self.add_field(
            name="Entries",
            value=str(DB().get_raffle_entry_count(self.guild_id)),
            inline=True,
        )
        self.add_field(
            name="Total Tickets", value=str(self.get_raffle_tickets()), inline=True
        )
        self.add_field(name="Global Odds", value=self.global_odds_str, inline=True)
        self.add_field(name="Role Odds", value=self.role_odds_str, inline=True)

    def get_raffle_tickets(self) -> int:
        entries = DB().get_raffle_entries(self.guild_id)
        return sum([e.tickets for e in entries])

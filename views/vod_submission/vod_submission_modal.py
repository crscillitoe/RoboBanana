from discord.ui import Modal, TextInput
from discord import TextStyle, Interaction
from datetime import datetime, timedelta
from discord import Object
import discord.utils

from db import DB, VodSubmission


class NewVodSubmissionModal(Modal, title="Submit a VOD for review!"):
    def __init__(self, client) -> None:
        super().__init__(timeout=None)
        self.client = client

        self.title_input = TextInput(
            label="AGENT | MAP | RANK",
            placeholder="Brimstone | Bind | Ascendant 3",
            style=TextStyle.short,
            required=True,
            min_length=1,
        )

        self.tracker_game_url = TextInput(
            label="Tracker.gg Account + Game + Heatmap Images",
            placeholder="tracker.gg/account\ntracker.gg/match\nimgur.com/heatmap.png",
            style=TextStyle.paragraph,
            required=True,
            min_length=1,
        )

        self.vod_url = TextInput(
            label="VOD Link + Positivity Timestamp",
            placeholder="youtube.com/my_awesome_vod\n00:00",
            style=TextStyle.paragraph,
            required=True,
            min_length=1,
        )

        # Paragraph
        self.extra = TextInput(
            label="Additional Information (Optional)",
            style=TextStyle.paragraph,
            required=False,
        )

        # Paragraph
        self.i_agree = TextInput(
            label="Please paste rule 11 here. And read it.",
            placeholder="I have read all of the rules....",
            style=TextStyle.paragraph,
            required=True,
        )

        self.add_item(self.i_agree)
        self.add_item(self.title_input)
        self.add_item(self.tracker_game_url)
        self.add_item(self.vod_url)
        self.add_item(self.extra)

    async def on_submit(self, interaction: Interaction) -> None:
        vod_rejected_role_id = 1055486151860953259
        role = discord.utils.get(interaction.user.roles, id=vod_rejected_role_id)
        if role is not None:
            await interaction.response.send_message(
                f"You currently have the VOD REJECTED role! You cannot submit a VOD"
                f" at this time.",
                ephemeral=True,
            )
            return

        banned_role_id = 1058462071202787441
        role = discord.utils.get(interaction.user.roles, id=banned_role_id)
        if role is not None:
            await interaction.response.send_message(
                f"You currently have the BANNED role! You cannot submit a VOD at"
                f" this time.",
                ephemeral=True,
            )
            return

        accepted_role = 1043260642968223794
        role = discord.utils.get(interaction.user.roles, id=accepted_role)
        if role is None:
            await interaction.response.send_message(
                f"You have not accepted the VOD Review rules!", ephemeral=True
            )
            return

        if "i have read all of the rules" not in self.i_agree.value.lower():
            await interaction.response.send_message(
                f"You didn't paste in rule 11.", ephemeral=True
            )
            return

        # Check that we can make the post (they dont have an active submission <1 week old)
        timestamp = DB().get_latest_timestamp(interaction.user.id)
        one_week_ago = datetime.now().date() - timedelta(days=6)

        if timestamp is not None and not timestamp.date() <= one_week_ago:
            # Bad, not enough time
            await interaction.response.send_message(
                f"You appear to have submitted a VOD less than one week ago. Try"
                f" again in one week.",
                ephemeral=True,
            )
            return

        # Makes the post
        vod_submissions_channel_id = 1055308028603269140

        await self.client.get_channel(vod_submissions_channel_id).create_thread(
            name=f"{self.title_input.value} | {interaction.user.name}",
            applied_tags=[Object(id=1104453647053619200)],
            content=f"""
Submission for {interaction.user.mention}

Account + Match + Consistency Heatmap:
{self.tracker_game_url.value}

VOD URL + POSITIVITY TIMESTAMP:
{self.vod_url.value}

Extra Information (Optional):
{self.extra.value}

User Agreement:
{self.i_agree.value}
""",
        )

        # Sets timestamp for that user at time.now()
        DB().update_timestamp(interaction.user.id)
        await interaction.response.send_message(
            f"Your VOD has been submitted! Thank you!", ephemeral=True
        )

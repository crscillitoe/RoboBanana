from discord import app_commands, Interaction, Client, User
from threading import Thread
from config import Config
import requests
import logging
from rdoclient import RandomOrgClient

PUBLISH_URL = "http://localhost:3000/publish-vod"
LOG = logging.getLogger(__name__)
AUTH_TOKEN = Config.CONFIG["Server"]["AuthToken"]
RANDOM_ORG_API_KEY = Config.CONFIG["RandomOrg"]["ApiKey"]
RANDOM_CLIENT = RandomOrgClient(RANDOM_ORG_API_KEY)


@app_commands.guild_only()
class VodCommands(app_commands.Group, name="vod"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @app_commands.command(name="start")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(username="username")
    @app_commands.describe(riotid="riotid")
    @app_commands.describe(rank="rank")
    async def vod(
        self, interaction: Interaction, username: str, riotid: str, rank: str
    ) -> None:
        """Start a VOD review for the given username"""
        Thread(
            target=publish_update,
            args=(
                username,
                riotid,
                rank,
                False,
            ),
        ).start()

        await interaction.response.send_message("VOD start event sent!", ephemeral=True)

    @app_commands.command(name="end")
    @app_commands.checks.has_role("Mod")
    async def complete(self, interaction: Interaction) -> None:
        """Start a VOD review for the given username"""
        Thread(
            target=publish_update,
            args=(
                "",
                "",
                "",
                True,
            ),
        ).start()

        await interaction.response.send_message(
            "VOD Complete Event sent!", ephemeral=True
        )

    @app_commands.command(name="get_rounds")
    @app_commands.checks.has_role("VOD Review Team")
    @app_commands.describe(rounds="total number of rounds in VOD")
    async def get_rounds(
        self, interaction: Interaction, rounds: int
    ) -> None:
        """Genereates rounds to check for Pre-round Comms requirement"""
        if (rounds < 21):
            await interaction.response.send_message("Not enough rounds in VOD. Match must be 13-8 or closer.\n;rejectedforfinalscore", ephemeral=True)
            return
        generatedList = RANDOM_CLIENT.generate_integers(rounds, 1, rounds, False)
        roundsToCheck = []
        checks = [True, True, True, True, True, True]
        returnString = "Pre-round Comms:"
        currentNum = 0
        for num in generatedList:
            currentNum = num
            if (3 < num and num < 13 and checks[2]):
                roundsToCheck.append(num)
                checks[2] = False
                continue
            elif (15 < num and checks[5]):
                roundsToCheck.append(num)
                checks[5] = False
                continue
            elif (num < 4 and (checks[0] or checks[1])):
                roundsToCheck.append(num)
                if (checks[0]):
                    checks[0] = False
                else:
                    checks[1] = False
                continue
            elif (12 < num and num < 16 and (checks[3] or checks[4])):
                roundsToCheck.append(num)
                if (checks[3]):
                    checks[3] = False
                else:
                    checks[4] = False
                continue
            if not any(checks):
                break #early break if all checks have been completed
        roundsToCheck.sort()
        for num in roundsToCheck:
            returnString += f"\nRound {num}:"

        await interaction.response.send_message(returnString, ephemeral=True)


def publish_update(username, riotid, rank, complete):
    payload = {
        "username": username,
        "riotid": riotid,
        "rank": rank,
        "complete": complete,
    }

    response = requests.post(
        url=PUBLISH_URL, json=payload, headers={"x-access-token": AUTH_TOKEN}
    )

    if response.status_code != 200:
        LOG.error(f"Failed to publish updated prediction summary: {response.text}")

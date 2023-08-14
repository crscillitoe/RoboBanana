from discord import app_commands, Interaction, Client, User
from threading import Thread
from config import Config
import requests
import logging
from rdoclient import RandomOrgClient

PUBLISH_URL = "http://localhost:3000/publish-vod"
LOG = logging.getLogger(__name__)
AUTH_TOKEN = Config.CONFIG["Server"]["AuthToken"]
RANDOM_CLIENT = RandomOrgClient("1c34f7d6-f990-48b7-97f0-e73e5c669d1f")


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

    @app_commands.command(name="rounds")
    @app_commands.checks.has_role("VOD Volunteer")
    @app_commands.describe(rounds="number of rounds in VOD")
    async def rounds(
        self, interaction: Interaction, rounds: int
    ) -> None:
        """Using Random.org, get rounds to be checked for VOD approval"""
        generatedList = RANDOM_CLIENT.generate_integers(rounds, 1, rounds, False)
        roundsToCheck = []
        checks = [False, False, False, False, False, False]
        returnString = "Pre-round Comms:"
        if (rounds < 21):
            await interaction.response.send_message(f"Not enough rounds in VOD\n;rejectedforfinalscore", ephemeral=True)
            return
        for num in generatedList:
            if (3 < num and num < 13 and not checks[2]):
                roundsToCheck.append(num)
                checks[2] = True
                continue
            elif (15 < num and not checks[5]):
                roundsToCheck.append(num)
                checks[5] = True
                continue
            elif (num < 4 and (not checks[0] or not checks[1])):
                roundsToCheck.append(num)
                if (checks[0]):
                    checks[1] = True
                else:
                    checks[0] = True
                continue
            elif (12 < num and num < 16 and (not checks[3] or not checks[4])):
                roundsToCheck.append(num)
                if (checks[3]):
                    checks[4] = True
                else:
                    checks[3] = True
                continue
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

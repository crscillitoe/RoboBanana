from datetime import datetime, timedelta
from discord import app_commands, Interaction, Client, User
from discord.app_commands.errors import AppCommandError, CheckFailure
from controllers.good_morning_controller import (
    GoodMorningController,
    GOOD_MORNING_EXPLANATION,
)
from controllers.prediction_controller import PredictionController
from db import DB, RaffleType
from db.models import PredictionChoice, PredictionOutcome
from views.predictions.create_predictions_modal import CreatePredictionModal
from views.raffle.new_raffle_modal import NewRaffleModal
from views.rewards.add_reward_modal import AddRewardModal
from controllers.raffle_controller import RaffleController
from config import Config
import logging
import random
from threading import Thread
import requests
import enum

HOOJ_DISCORD_ID = 82969926125490176

def get_processed_string(string):
    toRemove = [
        "\n",
        ".",
        ",",
        "!",
        "?",
        "[",
        "]",
        "*",
        ";",
        ":",
        "(",
        ")",
        "^",
        '"',
        "'",
    ]
    toReturn = string
    for remove in toRemove:
        toReturn = toReturn.replace(remove, "")

    return toReturn.lower()

class MemeCommands(app_commands.Group, name="meme"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client
        self.chain = {}

    @staticmethod
    def check_hooj(interaction: Interaction) -> bool:
        return interaction.user.id == HOOJ_DISCORD_ID

    @app_commands.command(name="generate_chain")
    @app_commands.checks.has_role("Mod")
    async def generate_chain(self, interaction: Interaction) -> None:
        if not self.check_hooj(interaction):
            return

        await interaction.response.send_message("Generating chain...", ephemeral=True)
        the_ones_who_know = 1036748993297920041
        channel = self.client.get_channel(the_ones_who_know)

        count = 1
        user_words = []
        async for message in channel.history(limit=8000):
            print(count)
            if message.author.id == HOOJ_DISCORD_ID:
                content = message.content
                for w in get_processed_string(content).split(" "):
                    if len(w) < 12:
                        user_words.append(w)
            count += 1

        index = 1
        for word in user_words[index:]:
            key = user_words[index - 1]
            if key in self.chain:
                self.chain[key].append(word)
            else:
                self.chain[key] = [word]

            index += 1

        await interaction.response.send_message("Chain generated!", ephemeral=True)

    @app_commands.command(name="hooj_message")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(length="length of message")
    async def hooj_message(self, interaction: Interaction, length: int) -> None:
        if not self.check_hooj(interaction):
            return

        word1 = random.choice(list(self.chain.keys()))
        message = word1.capitalize()

        while len(message.split(" ")) < length:
            if word1 != "":
                try:
                    fail = True
                    for i in range(100):
                        try:
                            word2 = random.choice(self.chain[word1])
                            fail = False
                            break
                        except:
                            continue
                    if fail:
                        raise Exception()
                except:
                    break

                word1 = word2
                message += " " + word2
            else:
                word1 = random.choice(self.chain[word1])

        await interaction.response.send_message(f"HOOJ BOT SAYS: {message} /s")


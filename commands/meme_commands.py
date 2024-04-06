import logging
from discord import app_commands, Interaction, Client
import random
from discord.app_commands.errors import AppCommandError, CheckFailure

from config import YAMLConfig as Config

HOOJ_DISCORD_ID = 82969926125490176
MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]
# these are hardcoded until raze to radiant is over, or config file changes are allowed
# for testing on own setup, these need to be changed to your appropriate IDs
# HIDDEN_MOD_ROLE should be 1040337265790042172 when committing and refers to the Mod (Role Hidden)
HIDDEN_MOD_ROLE = 1040337265790042172


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

    async def on_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, CheckFailure):
            return await interaction.response.send_message(
                "Failed to perform command - please verify permissions.", ephemeral=True
            )
        logging.error(error)
        return await super().on_error(interaction, error)

    @staticmethod
    def check_hooj(interaction: Interaction) -> bool:
        return interaction.user.id == HOOJ_DISCORD_ID

    @app_commands.command(name="generate_chain")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
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
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
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

import logging
from discord import Client, Intents, Message

from server.blueprints.chat import publish_chat

from config import Config

LOG = logging.getLogger(__name__)


class ServerBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True

        super().__init__(intents=intents)

    async def on_ready(self):
        LOG.info(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_message(self, message: Message):
        stream = False
        test = False
        if message.channel.id == 915336728707989537:
            test = True

        if message.channel.id == 1037040541017309225:
            stream = True


        # Valorant Discussion Channel (high volume good for testing)
        if stream or test:
            to_send = {
                "content": message.content,
                "authorNick": message.author.nick,
                "authorName": message.author.name,
                "displayName": message.author.display_name,
                "roles": [
                    {
                        "colorR": r.color.r,
                        "colorG": r.color.g,
                        "colorB": r.color.b,
                        "icon": None if r.icon is None else r.icon.url,
                        "id": r.id,
                        "name": r.name
                    } for r in message.author.roles],
                "stickers": [
                    {
                        "url": s.url
                    } for s in message.stickers]
            }
            await publish_chat(to_send, stream)


async def start_discord_client(client: Client):
    async with client:
        await client.start(Config.CONFIG["Discord"]["Token"])


DISCORD_CLIENT = ServerBot()

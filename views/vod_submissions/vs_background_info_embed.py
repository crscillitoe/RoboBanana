import json
from discord import Embed
from datetime import datetime

import discord
from db import DB

with open('./files/vod_submission/vs_background_info.json', 'r') as f:
    data = json.load(f)

class VsBackgroundInfoEmbed(Embed):
    def __init__(
        self,
        guild_id: int,
    ):
        super().__init__(
            title=data['title'],
            description=data['description'],
            color=discord.Colour.yellow(),
            type='rich'
        )

        self.guild_id = guild_id

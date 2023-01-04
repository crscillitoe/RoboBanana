from discord import Embed

import discord

class VsGenericEmbed(Embed):
    def __init__(
        self,
        guild_id: int,
        json: any,
    ):
        super().__init__(
            title=json['title'],
            description=json['description'],
            color=discord.Colour.yellow(),
            type='rich'
        )

        self.guild_id = guild_id

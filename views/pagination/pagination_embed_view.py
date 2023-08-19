from discord import Embed, ButtonStyle
from discord.ui import View, button

class PaginationEmbed(Embed):
    def __init__(self, title, data_list, per_page=10):
        super().__init__()
        self.base_title = title
        self.data_list = data_list
        self.per_page = per_page
        self.num_pages = (len(data_list) + per_page - 1) // per_page
        self.current_page = 0

    async def build_embed(self):
        self.title = await self.build_title()
        self.description = await self.build_description()
        return self

    async def build_title(self):
        title = self.base_title
        if self.num_pages > 1:
            title += f"\t\t(Page {self.current_page + 1}/{self.num_pages})\n"
        return title

    async def build_description(self):
        start_idx = self.current_page * self.per_page
        end_idx = start_idx + self.per_page
        description = "".join(self.data_list[start_idx:end_idx])
        return description


class PaginationView(View):
    def __init__(self, interaction, pagination_embed):
        super().__init__()
        self.interaction = interaction
        self.embed = pagination_embed
        self.next_button.disabled = self.embed.num_pages == 1

    @button(label="Previous", style=ButtonStyle.secondary, disabled=True)
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        if self.embed.current_page > 0:
            self.embed.current_page -= 1
            await self.update_embed()

    @button(label="Next", style=ButtonStyle.secondary)
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        if self.embed.current_page < self.embed.num_pages - 1:
            self.embed.current_page += 1
            await self.update_embed()

    async def update_embed(self):
        embed = await self.embed.build_embed()
        message = await self.interaction.original_response()
        self.prev_button.disabled = self.embed.current_page == 0
        self.next_button.disabled = self.embed.current_page == self.embed.num_pages - 1
        await message.edit(embed=embed, view=self)
        
    async def on_timeout(self):
        self.next_button.disabled = True
        self.prev_button.disabled = True
        message = await self.interaction.original_response()
        await message.edit(embed=self.embed, view=self)
        self.stop()

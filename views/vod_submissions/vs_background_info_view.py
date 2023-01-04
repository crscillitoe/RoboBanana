from discord.ui import View
from .vs_background_info_embed import VsBackgroundInfoEmbed

class VsBackgroundInfoView(View):
    def __init__(
        self, parent: VsBackgroundInfoEmbed
    ) -> None:
        super().__init__(timeout=None)

        self.parent = parent
        

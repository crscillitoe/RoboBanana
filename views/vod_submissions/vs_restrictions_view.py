from discord.ui import View
from .vs_restrictions_embed import VsRestrictionsEmbed

class VsRestrictionsView(View):
    def __init__(
        self, parent: VsRestrictionsEmbed
    ) -> None:
        super().__init__(timeout=None)

        self.parent = parent
        

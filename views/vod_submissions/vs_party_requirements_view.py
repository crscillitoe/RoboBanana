from discord.ui import View
from .vs_party_requirements_embed import VsPartyRequirementsEmbed

class VsPartyRequirementsView(View):
    def __init__(
        self, parent: VsPartyRequirementsEmbed
    ) -> None:
        super().__init__(timeout=None)

        self.parent = parent
        

import discord
from discord import app_commands
import os
from db import authorized, make_embed, set_field, load
from views import ConfigView

intents = discord.Intents.default()
intents.members   = True
intents.presences = True

class MultiBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.add_view(ConfigView())
        print("[MultiBot] Slash commands synchronisées ✅")

    async def on_ready(self):
        print(f"[MultiBot] Connecté : {self.user} ({self.user.id})")
        await self.change_presence(activity=discord.Game(name="/dmall"))

bot = MultiBot()

# ── Slash commands ─────────────────────────────────────────────────────────────

@bot.tree.command(name="dmall", description="Ouvrir le panel de configuration MultiDmall")
async def cmd_dmall(interaction: discord.Interaction):
    if not await authorized(interaction.user.id):
        await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)
        return
    await interaction.response.send_message(
        embed=await make_embed(),
        view=ConfigView()
    )

@bot.tree.command(name="authorize", description="Autoriser un utilisateur")
@app_commands.describe(user="L'utilisateur à autoriser")
async def cmd_authorize(interaction: discord.Interaction, user: discord.User):
    cfg = await load()
    auth = cfg.get("authorized_users", [])
    if auth and interaction.user.id not in auth:
        await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)
        return
    if user.id not in auth:
        auth.append(user.id)
        await set_field("authorized_users", auth)
    await interaction.response.send_message(f"✅ **{user}** autorisé.", ephemeral=True)

@bot.tree.command(name="clearids", description="Vider la liste des User IDs cibles")
async def cmd_clearids(interaction: discord.Interaction):
    if not await authorized(interaction.user.id):
        await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)
        return
    await set_field("user_ids", [])
    await interaction.response.send_message("✅ Liste des User IDs vidée.", ephemeral=True)

@bot.tree.command(name="cleartokens", description="Vider la liste des tokens")
async def cmd_cleartokens(interaction: discord.Interaction):
    if not await authorized(interaction.user.id):
        await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)
        return
    await set_field("tokens", [])
    await interaction.response.send_message("✅ Tokens vidés.", ephemeral=True)

@bot.tree.command(name="reset", description="Réinitialiser toute la configuration")
async def cmd_reset(interaction: discord.Interaction):
    if not await authorized(interaction.user.id):
        await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)
        return
    from db import DEFAULT, save
    import copy
    await save(copy.deepcopy(DEFAULT))
    await interaction.response.send_message("✅ Configuration réinitialisée.", ephemeral=True)

def run():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ BOT_TOKEN manquant dans les variables d'environnement !")
    bot.run(token)

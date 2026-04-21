import discord
from discord import app_commands
import os
from db import authorized, make_embed, set_field, load
from views import ConfigView, send_config_panel

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
        await self.change_presence(
            activity=discord.Streaming(name="ohio on top", url="https://twitch.tv/ohio")
        )

bot = MultiBot()

# ── Slash commands ─────────────────────────────────────────────────────────────

@bot.tree.command(name="dmall", description="Ouvrir le panel de configuration DMall Ohio")
async def cmd_dmall(interaction: discord.Interaction):
    if not await authorized(interaction.user.id):
        await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)
        return
    await send_config_panel(interaction)

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

@bot.tree.command(name="delete", description="Supprimer tous les salons d'une catégorie")
@app_commands.describe(category_id="L'ID de la catégorie à vider")
async def cmd_delete(interaction: discord.Interaction, category_id: str):
    if not await authorized(interaction.user.id):
        await interaction.response.send_message("❌ Non autorisé.", ephemeral=True)
        return
    if not interaction.guild:
        await interaction.response.send_message("❌ Commande réservée aux serveurs.", ephemeral=True)
        return

    try:
        cat_id = int(category_id)
    except ValueError:
        await interaction.response.send_message("❌ ID invalide.", ephemeral=True)
        return

    category = interaction.guild.get_channel(cat_id)
    if not category or not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message("❌ Catégorie introuvable.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    deleted = 0
    errors  = 0
    for channel in list(category.channels):
        try:
            await channel.delete(reason=f"Suppression via /delete par {interaction.user}")
            deleted += 1
        except Exception:
            errors += 1

    msg = f"✅ **{deleted}** salon(s) supprimé(s) dans **{category.name}**."
    if errors:
        msg += f"\n⚠️ **{errors}** salon(s) n'ont pas pu être supprimés (permissions manquantes)."
    await interaction.followup.send(msg, ephemeral=True)

def run():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ BOT_TOKEN manquant dans les variables d'environnement !")
    bot.run(token)

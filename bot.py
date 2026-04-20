import discord
from discord import app_commands, ui
import asyncio
import os
import motor.motor_asyncio
from dotenv import load_dotenv

load_dotenv()

# ── MongoDB ───────────────────────────────────────────────────────────────────

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = mongo_client["multidmall"]
config_col = db["config"]

CONFIG_ID = "main"

DEFAULT_CONFIG = {
    "_id": CONFIG_ID,
    "tokens": [],
    "message": "",
    "embed": {
        "enabled": False,
        "title": "",
        "description": "",
        "color": 5814783,
        "footer": "",
        "image_url": "",
        "thumbnail_url": ""
    },
    "user_ids": [],
    "ignore_ids": [],
    "dm_options": {
        "delay": 1.5,
        "stop_on_error": False,
        "max_errors": 10
    },
    "status": "",
    "authorized_users": []
}

async def load_config() -> dict:
    doc = await config_col.find_one({"_id": CONFIG_ID})
    if doc is None:
        await config_col.insert_one(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()
    return doc

async def save_config(data: dict):
    data["_id"] = CONFIG_ID
    await config_col.replace_one({"_id": CONFIG_ID}, data, upsert=True)

async def update_field(field: str, value):
    await config_col.update_one(
        {"_id": CONFIG_ID},
        {"$set": {field: value}},
        upsert=True
    )

async def is_authorized(user_id: int) -> bool:
    cfg = await load_config()
    auth = cfg.get("authorized_users", [])
    return len(auth) == 0 or user_id in auth

# ── Embed builder ─────────────────────────────────────────────────────────────

async def make_config_embed() -> discord.Embed:
    cfg = await load_config()
    embed = discord.Embed(
        title="⬡  Configuration du MultiDmall",
        description="*Utilisez les boutons ci-dessous pour configurer votre Dmall.*",
        color=0x5865F2
    )
    nb_tokens = len(cfg.get("tokens", []))
    embed.add_field(
        name="🤖 Tokens",
        value=f"`{nb_tokens}` token(s) configuré(s)" if nb_tokens else "*Aucun token ajouté*",
        inline=False
    )
    msg = cfg.get("message", "")
    embed.add_field(
        name="📩 Message",
        value=f"```{msg[:100]}{'...' if len(msg) > 100 else ''}```" if msg else "*Aucun message défini*",
        inline=False
    )
    emb_cfg = cfg.get("embed", {})
    embed.add_field(
        name="📝 Embed",
        value=f"`{emb_cfg.get('title', '')[:80]}`" if emb_cfg.get("enabled") and emb_cfg.get("title") else "*Aucun embed défini*",
        inline=False
    )
    nb_ids     = len(cfg.get("user_ids", []))
    nb_ignored = len(cfg.get("ignore_ids", []))
    delay      = cfg.get("dm_options", {}).get("delay", 1.5)
    embed.add_field(name="👤 User IDs",           value=f"Total : **{nb_ids} ID**",     inline=True)
    embed.add_field(name="🚫 User IDs à Ignorer", value=f"Total : **{nb_ignored} ID**", inline=True)
    embed.add_field(name="⚙️ Options de DM",       value=f"Délai : **{delay}s**",        inline=True)
    status = cfg.get("status", "")
    embed.set_footer(text=f"MultiBot | discord.gg/sponsorbot{' | ' + status if status else ''}")
    return embed

# ── Modals ────────────────────────────────────────────────────────────────────

class TokensModal(ui.Modal, title="🤖 Ajouter des tokens"):
    tokens_input = ui.TextInput(
        label="Tokens (un par ligne)",
        style=discord.TextStyle.paragraph,
        placeholder="token1\ntoken2\n...",
        required=True,
        max_length=4000
    )
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load_config()
        new_tokens = [t.strip() for t in self.tokens_input.value.split("\n") if t.strip()]
        added = 0
        for t in new_tokens:
            if t not in cfg["tokens"]:
                cfg["tokens"].append(t)
                added += 1
        await save_config(cfg)
        await interaction.response.edit_message(embed=await make_config_embed(), view=ConfigView())
        await interaction.followup.send(f"✅ **{added}** token(s) ajouté(s). Total : **{len(cfg['tokens'])}**", ephemeral=True)

class MessageModal(ui.Modal, title="📩 Définir le message"):
    message_input = ui.TextInput(
        label="Message à envoyer en DM",
        style=discord.TextStyle.paragraph,
        placeholder="Salut ! Voici mon message...",
        required=False,
        max_length=2000
    )
    async def on_submit(self, interaction: discord.Interaction):
        await update_field("message", self.message_input.value.strip())
        await interaction.response.edit_message(embed=await make_config_embed(), view=ConfigView())
        await interaction.followup.send("✅ Message défini.", ephemeral=True)

class EmbedModal(ui.Modal, title="📝 Configurer l'Embed"):
    embed_title  = ui.TextInput(label="Titre", placeholder="Titre de l'embed", required=False, max_length=256)
    embed_desc   = ui.TextInput(label="Description", style=discord.TextStyle.paragraph, placeholder="Description...", required=False, max_length=4000)
    embed_color  = ui.TextInput(label="Couleur hex (ex: #5865F2)", placeholder="#5865F2", required=False, max_length=10)
    embed_footer = ui.TextInput(label="Footer", placeholder="Mon footer", required=False, max_length=256)
    embed_img    = ui.TextInput(label="URL image (optionnel)", placeholder="https://...", required=False, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        title = self.embed_title.value.strip()
        try:
            color_str = self.embed_color.value.strip().lstrip("#")
            color = int(color_str, 16) if color_str else 5814783
        except:
            color = 5814783
        new_embed = {
            "enabled":       bool(title or self.embed_desc.value.strip()),
            "title":         title,
            "description":   self.embed_desc.value.strip(),
            "color":         color,
            "footer":        self.embed_footer.value.strip(),
            "image_url":     self.embed_img.value.strip(),
            "thumbnail_url": ""
        }
        await update_field("embed", new_embed)
        await interaction.response.edit_message(embed=await make_config_embed(), view=ConfigView())
        await interaction.followup.send("✅ Embed configuré.", ephemeral=True)

class UserIDsModal(ui.Modal, title="👤 Ajouter des User IDs"):
    ids_input = ui.TextInput(
        label="User IDs (un par ligne)",
        style=discord.TextStyle.paragraph,
        placeholder="123456789\n987654321\n...",
        required=True,
        max_length=4000
    )
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load_config()
        added, errors = 0, 0
        for line in self.ids_input.value.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                uid = int(line)
                if uid not in cfg["user_ids"]:
                    cfg["user_ids"].append(uid)
                    added += 1
            except:
                errors += 1
        await save_config(cfg)
        await interaction.response.edit_message(embed=await make_config_embed(), view=ConfigView())
        msg = f"✅ **{added}** ID(s) ajouté(s). Total : **{len(cfg['user_ids'])}**"
        if errors:
            msg += f"\n⚠️ **{errors}** ligne(s) invalide(s) ignorée(s)."
        await interaction.followup.send(msg, ephemeral=True)

class IgnoreIDsModal(ui.Modal, title="🚫 IDs à Ignorer"):
    ids_input = ui.TextInput(
        label="User IDs à ignorer (un par ligne)",
        style=discord.TextStyle.paragraph,
        placeholder="123456789\n...",
        required=True,
        max_length=4000
    )
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load_config()
        added = 0
        for line in self.ids_input.value.split("\n"):
            try:
                uid = int(line.strip())
                if uid not in cfg["ignore_ids"]:
                    cfg["ignore_ids"].append(uid)
                    added += 1
            except:
                pass
        await save_config(cfg)
        await interaction.response.edit_message(embed=await make_config_embed(), view=ConfigView())
        await interaction.followup.send(f"✅ **{added}** ID(s) ignoré(s). Total : **{len(cfg['ignore_ids'])}**", ephemeral=True)

class DMOptionsModal(ui.Modal, title="⚙️ Options de DM"):
    delay      = ui.TextInput(label="Délai entre DMs (secondes)", placeholder="1.5", required=False, max_length=10)
    max_errors = ui.TextInput(label="Nombre max d'erreurs", placeholder="10", required=False, max_length=5)
    stop_err   = ui.TextInput(label="Stopper si trop d'erreurs ? (oui/non)", placeholder="non", required=False, max_length=5)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load_config()
        try:    cfg["dm_options"]["delay"]      = float(self.delay.value.strip() or 1.5)
        except: pass
        try:    cfg["dm_options"]["max_errors"] = int(self.max_errors.value.strip() or 10)
        except: pass
        stop_val = self.stop_err.value.strip().lower()
        cfg["dm_options"]["stop_on_error"] = stop_val in ("oui", "o", "yes", "y", "true")
        await save_config(cfg)
        await interaction.response.edit_message(embed=await make_config_embed(), view=ConfigView())
        await interaction.followup.send("✅ Options de DM sauvegardées.", ephemeral=True)

class StatusModal(ui.Modal, title="⭐ Définir le status"):
    status_input = ui.TextInput(
        label="Status du selfbot",
        placeholder="En train de DM...",
        required=False,
        max_length=128
    )
    async def on_submit(self, interaction: discord.Interaction):
        await update_field("status", self.status_input.value.strip())
        await interaction.response.edit_message(embed=await make_config_embed(), view=ConfigView())
        await interaction.followup.send("✅ Status défini.", ephemeral=True)

class ClearModal(ui.Modal, title="🗑️ Réinitialiser"):
    confirm = ui.TextInput(label='Tapez "CONFIRMER" pour réinitialiser', placeholder="CONFIRMER", required=True, max_length=20)
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.strip().upper() == "CONFIRMER":
            fresh = DEFAULT_CONFIG.copy()
            fresh["_id"] = CONFIG_ID
            fresh["embed"] = DEFAULT_CONFIG["embed"].copy()
            fresh["dm_options"] = DEFAULT_CONFIG["dm_options"].copy()
            await save_config(fresh)
            await interaction.response.edit_message(embed=await make_config_embed(), view=ConfigView())
            await interaction.followup.send("✅ Configuration réinitialisée.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Confirmation incorrecte.", ephemeral=True)

# ── View (Buttons) ────────────────────────────────────────────────────────────

class ConfigView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def check_auth(self, interaction: discord.Interaction) -> bool:
        if not await is_authorized(interaction.user.id):
            await interaction.response.send_message("❌ Tu n'es pas autorisé à utiliser ce panel.", ephemeral=True)
            return False
        return True

    @ui.button(label="➕ Ajouter des tokens", style=discord.ButtonStyle.primary,   custom_id="mdm_tokens",    row=0)
    async def btn_tokens(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_auth(interaction): return
        await interaction.response.send_modal(TokensModal())

    @ui.button(label="📩 Définir le message", style=discord.ButtonStyle.success,   custom_id="mdm_message",   row=0)
    async def btn_message(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_auth(interaction): return
        await interaction.response.send_modal(MessageModal())

    @ui.button(label="📝 Embed",              style=discord.ButtonStyle.secondary,  custom_id="mdm_embed",     row=1)
    async def btn_embed(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_auth(interaction): return
        await interaction.response.send_modal(EmbedModal())

    @ui.button(label="👤 User IDs",           style=discord.ButtonStyle.secondary,  custom_id="mdm_userids",   row=1)
    async def btn_userids(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_auth(interaction): return
        await interaction.response.send_modal(UserIDsModal())

    @ui.button(label="🚫 IDs à ignorer",      style=discord.ButtonStyle.secondary,  custom_id="mdm_ignore",    row=1)
    async def btn_ignore(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_auth(interaction): return
        await interaction.response.send_modal(IgnoreIDsModal())

    @ui.button(label="⚙️ Options DM",         style=discord.ButtonStyle.secondary,  custom_id="mdm_dmoptions", row=2)
    async def btn_dmoptions(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_auth(interaction): return
        await interaction.response.send_modal(DMOptionsModal())

    @ui.button(label="⭐ Status",             style=discord.ButtonStyle.secondary,  custom_id="mdm_status",    row=2)
    async def btn_status(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_auth(interaction): return
        await interaction.response.send_modal(StatusModal())

    @ui.button(label="🗑️ Reset",             style=discord.ButtonStyle.danger,     custom_id="mdm_clear",     row=2)
    async def btn_clear(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_auth(interaction): return
        await interaction.response.send_modal(ClearModal())

    @ui.button(label="🚀 DMall",              style=discord.ButtonStyle.danger,     custom_id="mdm_dmall",     row=3)
    async def btn_dmall(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_auth(interaction): return
        cfg = await load_config()
        errors = []
        if not cfg.get("tokens"):   errors.append("❌ Aucun token configuré.")
        if not cfg.get("user_ids"): errors.append("❌ Aucun User ID défini.")
        if not cfg.get("message") and not cfg.get("embed", {}).get("enabled"):
            errors.append("❌ Ni message ni embed défini.")
        if errors:
            await interaction.response.send_message("\n".join(errors), ephemeral=True)
            return
        await interaction.response.send_message(
            f"🚀 **DMall lancé !** `{len(cfg['tokens'])}` token(s) → `{len(cfg['user_ids'])}` cibles",
            ephemeral=True
        )
        asyncio.create_task(launch_dmall(cfg, interaction))

# ── Selfbot DMall runner ──────────────────────────────────────────────────────

async def run_one_token(token: str, cfg: dict, index: int) -> dict:
    import discord as _dc
    client = _dc.Client()
    results = {"sent": 0, "errors": 0}

    @client.event
    async def on_ready():
        ignore_ids = set(cfg.get("ignore_ids", []))
        delay      = cfg["dm_options"]["delay"]
        max_errors = cfg["dm_options"]["max_errors"]

        if cfg.get("status"):
            await client.change_presence(activity=_dc.Game(name=cfg["status"]))

        for uid in cfg.get("user_ids", []):
            if uid in ignore_ids:
                continue
            try:
                user = await client.fetch_user(uid)
                dm   = await user.create_dm()
                emb  = None
                emb_cfg = cfg.get("embed", {})
                if emb_cfg.get("enabled"):
                    emb = _dc.Embed(
                        title=emb_cfg.get("title", ""),
                        description=emb_cfg.get("description", ""),
                        color=emb_cfg.get("color", 5814783)
                    )
                    if emb_cfg.get("footer"):        emb.set_footer(text=emb_cfg["footer"])
                    if emb_cfg.get("image_url"):     emb.set_image(url=emb_cfg["image_url"])
                    if emb_cfg.get("thumbnail_url"): emb.set_thumbnail(url=emb_cfg["thumbnail_url"])
                await dm.send(content=cfg.get("message") or None, embed=emb)
                results["sent"] += 1
                print(f"[Token {index+1}] ✅ DM → {user} ({uid})")
            except _dc.Forbidden:
                results["errors"] += 1
                print(f"[Token {index+1}] ❌ DM fermés : {uid}")
            except Exception as e:
                results["errors"] += 1
                print(f"[Token {index+1}] ❌ Erreur {uid}: {e}")

            if results["errors"] >= max_errors and cfg["dm_options"]["stop_on_error"]:
                print(f"[Token {index+1}] 🛑 Trop d'erreurs.")
                break
            await asyncio.sleep(delay)

        await client.close()

    try:
        await client.start(token, bot=False)
    except Exception as e:
        print(f"[Token {index+1}] ❌ Token invalide: {e}")
        results["errors"] += 1

    return results

async def launch_dmall(cfg: dict, interaction: discord.Interaction):
    tasks   = [run_one_token(tok, cfg, i) for i, tok in enumerate(cfg["tokens"])]
    results = await asyncio.gather(*tasks)

    total_sent   = sum(r["sent"]   for r in results)
    total_errors = sum(r["errors"] for r in results)

    embed = discord.Embed(
        title="🚀 DMall Terminé",
        color=0x57F287 if total_errors == 0 else 0xED4245
    )
    embed.add_field(name="✅ DMs envoyés",     value=str(total_sent),          inline=True)
    embed.add_field(name="❌ Erreurs",         value=str(total_errors),        inline=True)
    embed.add_field(name="🤖 Tokens utilisés", value=str(len(cfg["tokens"])), inline=True)
    embed.set_footer(text="MultiBot | discord.gg/sponsorbot")
    try:
        await interaction.followup.send(embed=embed)
    except:
        pass

# ── Bot client ────────────────────────────────────────────────────────────────

class MultiBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.add_view(ConfigView())
        print("[MultiBot] Slash commands synchronisées ✅")

    async def on_ready(self):
        print(f"[MultiBot] Connecté : {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Game(name="/dmall"))

bot = MultiBot()

# ── Slash commands ────────────────────────────────────────────────────────────

@bot.tree.command(name="dmall", description="Ouvrir le panel de configuration MultiDmall")
async def cmd_dmall(interaction: discord.Interaction):
    if not await is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Tu n'es pas autorisé.", ephemeral=True)
        return
    await interaction.response.send_message(
        content="**MultiBot** | Support : discord.gg/sponsorbot",
        embed=await make_config_embed(),
        view=ConfigView()
    )

@bot.tree.command(name="authorize", description="Autoriser un utilisateur à utiliser le DMall")
@app_commands.describe(user="L'utilisateur à autoriser")
async def cmd_authorize(interaction: discord.Interaction, user: discord.User):
    cfg = await load_config()
    auth = cfg.get("authorized_users", [])
    if auth and interaction.user.id not in auth:
        await interaction.response.send_message("❌ Seul un utilisateur autorisé peut en autoriser d'autres.", ephemeral=True)
        return
    if user.id not in auth:
        auth.append(user.id)
        await update_field("authorized_users", auth)
    await interaction.response.send_message(f"✅ **{user}** est maintenant autorisé.", ephemeral=True)

@bot.tree.command(name="clearids", description="Vider la liste des User IDs cibles")
async def cmd_clearids(interaction: discord.Interaction):
    if not await is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Tu n'es pas autorisé.", ephemeral=True)
        return
    await update_field("user_ids", [])
    await interaction.response.send_message("✅ Liste des User IDs vidée.", ephemeral=True)

@bot.tree.command(name="cleartokens", description="Vider la liste des tokens")
async def cmd_cleartokens(interaction: discord.Interaction):
    if not await is_authorized(interaction.user.id):
        await interaction.response.send_message("❌ Tu n'es pas autorisé.", ephemeral=True)
        return
    await update_field("tokens", [])
    await interaction.response.send_message("✅ Tokens vidés.", ephemeral=True)

# ── Entry point ───────────────────────────────────────────────────────────────

def run():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ Variable d'environnement BOT_TOKEN manquante !")
    bot.run(token)

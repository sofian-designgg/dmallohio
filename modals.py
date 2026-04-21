import discord
from discord import ui
import asyncio
from db import load, save, set_field

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _refresh_config(interaction: discord.Interaction):
    """Rafraîchit le panel principal en Components V2 après un modal."""
    from views import send_config_panel
    await send_config_panel(interaction)

async def _refresh_embed_builder(interaction: discord.Interaction):
    """Rafraîchit le panel Embed Builder en Components V2 après un modal."""
    from views import send_embed_builder_panel
    await send_embed_builder_panel(interaction)

# ── Simple modals ─────────────────────────────────────────────────────────────

class TokensModal(ui.Modal, title="🤖 Ajouter des tokens"):
    tokens_input = ui.TextInput(label="Tokens (un par ligne)",
        style=discord.TextStyle.paragraph, placeholder="token1\ntoken2", required=True, max_length=4000)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load()
        added = 0
        for t in self.tokens_input.value.split("\n"):
            t = t.strip()
            if t and t not in cfg["tokens"]:
                cfg["tokens"].append(t); added += 1
        await save(cfg)
        await _refresh_config(interaction)
        await interaction.followup.send(f"✅ **{added}** token(s) ajouté(s). Total : **{len(cfg['tokens'])}**", ephemeral=True)

class SimpleMessageModal(ui.Modal, title="📩 Saisir le message"):
    msg = ui.TextInput(label="Message à envoyer en DM",
        style=discord.TextStyle.paragraph,
        placeholder="Salut {user} ! Voici mon message...\n\nVariables : {user} {user.id} {timestamp}",
        required=False, max_length=2000)

    async def on_submit(self, interaction: discord.Interaction):
        await set_field("message", self.msg.value.strip())
        await set_field("embed", {"enabled": False, "title": "", "description": "",
                                  "color": 5814783, "footer": "", "image_url": "",
                                  "thumbnail_url": "", "button_label": "", "button_url": ""})
        await _refresh_config(interaction)
        await interaction.followup.send("✅ Message défini avec succès.", ephemeral=True)

class EmbedJSONModal(ui.Modal, title="📝 Embed JSON"):
    raw = ui.TextInput(label="JSON de l'embed",
        style=discord.TextStyle.paragraph,
        placeholder='{"title":"Titre","description":"Desc","color":5814783}',
        required=True, max_length=4000)

    async def on_submit(self, interaction: discord.Interaction):
        import json
        try:
            data = json.loads(self.raw.value.strip())
            emb = {
                "enabled": True,
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "color": data.get("color", 5814783),
                "footer": data.get("footer", {}).get("text", "") if isinstance(data.get("footer"), dict) else data.get("footer", ""),
                "image_url": data.get("image", {}).get("url", "") if isinstance(data.get("image"), dict) else "",
                "thumbnail_url": data.get("thumbnail", {}).get("url", "") if isinstance(data.get("thumbnail"), dict) else "",
                "button_label": "", "button_url": ""
            }
            await set_field("embed", emb)
            await set_field("message", "")
            await _refresh_config(interaction)
            await interaction.followup.send("✅ Embed JSON importé.", ephemeral=True)
        except Exception as ex:
            await interaction.response.send_message(f"❌ JSON invalide : `{ex}`", ephemeral=True)

class EmbedTitleModal(ui.Modal, title="✏️ Titre de l'embed"):
    title_in = ui.TextInput(label="Titre", placeholder="Mon super titre", required=False, max_length=256)
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load()
        cfg["embed"]["title"] = self.title_in.value.strip()
        cfg["embed"]["enabled"] = True
        await save(cfg)
        await _refresh_embed_builder(interaction)
        await interaction.followup.send(f"✅ Titre : `{self.title_in.value.strip()}`", ephemeral=True)

class EmbedDescModal(ui.Modal, title="📄 Description de l'embed"):
    desc_in = ui.TextInput(label="Description", style=discord.TextStyle.paragraph,
        placeholder="Description...\n\nVariables : {user} {user.id} {timestamp}",
        required=False, max_length=4000)
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load()
        cfg["embed"]["description"] = self.desc_in.value.strip()
        cfg["embed"]["enabled"] = True
        await save(cfg)
        await _refresh_embed_builder(interaction)
        await interaction.followup.send("✅ Description définie.", ephemeral=True)

class EmbedColorImageModal(ui.Modal, title="🎨 Couleur & Image"):
    color_in = ui.TextInput(label="Couleur hex", placeholder="#5865F2", required=False, max_length=10)
    img_in   = ui.TextInput(label="URL de l'image", placeholder="https://...", required=False, max_length=500)
    footer_in= ui.TextInput(label="Footer", placeholder="Mon footer", required=False, max_length=256)
    btn_label= ui.TextInput(label="Bouton lien - texte", placeholder="Cliquez ici", required=False, max_length=80)
    btn_url  = ui.TextInput(label="Bouton lien - URL", placeholder="https://...", required=False, max_length=500)
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load()
        try:
            c = self.color_in.value.strip().lstrip("#")
            cfg["embed"]["color"] = int(c, 16) if c else 5814783
        except: cfg["embed"]["color"] = 5814783
        cfg["embed"]["image_url"]    = self.img_in.value.strip()
        cfg["embed"]["footer"]       = self.footer_in.value.strip()
        cfg["embed"]["button_label"] = self.btn_label.value.strip()
        cfg["embed"]["button_url"]   = self.btn_url.value.strip()
        cfg["embed"]["enabled"] = True
        await save(cfg)
        await _refresh_embed_builder(interaction)
        await interaction.followup.send("✅ Couleur & image configurées.", ephemeral=True)

class EmbedThumbnailModal(ui.Modal, title="🖼️ Thumbnail"):
    thumb = ui.TextInput(label="URL du thumbnail", placeholder="https://...", required=False, max_length=500)
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load()
        cfg["embed"]["thumbnail_url"] = self.thumb.value.strip()
        cfg["embed"]["enabled"] = True
        await save(cfg)
        await _refresh_embed_builder(interaction)
        await interaction.followup.send("✅ Thumbnail défini.", ephemeral=True)

class EmbedButtonModal(ui.Modal, title="🔗 Bouton lien"):
    btn_label = ui.TextInput(label="Texte du bouton", placeholder="Cliquez ici", required=False, max_length=80)
    btn_url   = ui.TextInput(label="URL du bouton", placeholder="https://...", required=False, max_length=500)
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load()
        cfg["embed"]["button_label"] = self.btn_label.value.strip()
        cfg["embed"]["button_url"]   = self.btn_url.value.strip()
        cfg["embed"]["enabled"] = True
        await save(cfg)
        await _refresh_embed_builder(interaction)
        await interaction.followup.send("✅ Bouton lien configuré.", ephemeral=True)

class UserIDsModal(ui.Modal, title="➕ Ajouter des User IDs"):
    ids = ui.TextInput(label="User IDs (un par ligne)",
        style=discord.TextStyle.paragraph, placeholder="123456789\n987654321", required=True, max_length=4000)
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load()
        added, bad = 0, 0
        for line in self.ids.value.split("\n"):
            try:
                uid = int(line.strip())
                if uid not in cfg["user_ids"]: cfg["user_ids"].append(uid); added += 1
            except: bad += 1
        await save(cfg)
        msg = f"✅ **{added}** ID(s) ajouté(s). Total : **{len(cfg['user_ids'])}**"
        if bad: msg += f"\n⚠️ **{bad}** ligne(s) invalide(s)."
        await interaction.response.send_message(msg, ephemeral=True)

class CustomDelayModal(ui.Modal, title="⚙️ DMall Custom - Délai"):
    delay = ui.TextInput(label="Délai personnalisé (secondes)", placeholder="3.0", required=True, max_length=10)
    def __init__(self, cfg):
        super().__init__(); self.cfg_data = cfg
    async def on_submit(self, interaction: discord.Interaction):
        from dmall import run_normal
        try: d = float(self.delay.value.strip())
        except: d = 1.5
        cfg = self.cfg_data.copy()
        cfg["dm_options"] = {**cfg.get("dm_options", {}), "delay": d}
        await interaction.response.send_message(f"🚀 **DMall Custom** lancé ! Délai : **{d}s**", ephemeral=True)
        asyncio.create_task(run_normal(cfg, interaction))

class IgnoreIDsModal(ui.Modal, title="🚫 IDs à ignorer"):
    ids = ui.TextInput(label="User IDs à ignorer (un par ligne)",
        style=discord.TextStyle.paragraph, placeholder="123456789", required=True, max_length=4000)
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load()
        added = 0
        for line in self.ids.value.split("\n"):
            try:
                uid = int(line.strip())
                if uid not in cfg["ignore_ids"]: cfg["ignore_ids"].append(uid); added += 1
            except: pass
        await save(cfg)
        await _refresh_config(interaction)
        await interaction.followup.send(f"✅ **{added}** ID(s) ignoré(s).", ephemeral=True)

class StatusModal(ui.Modal, title="⭐ Status du selfbot"):
    status = ui.TextInput(label="Status", placeholder="En train de DM...", required=False, max_length=128)
    async def on_submit(self, interaction: discord.Interaction):
        await set_field("status", self.status.value.strip())
        await _refresh_config(interaction)
        await interaction.followup.send("✅ Status défini.", ephemeral=True)

class DMOptionsModal(ui.Modal, title="⚙️ Options de DM"):
    delay  = ui.TextInput(label="Délai entre DMs (secondes)", placeholder="1.5", required=False, max_length=10)
    maxerr = ui.TextInput(label="Nombre max d'erreurs", placeholder="10", required=False, max_length=5)
    stop   = ui.TextInput(label="Stopper si trop d'erreurs ? (oui/non)", placeholder="non", required=False, max_length=5)
    async def on_submit(self, interaction: discord.Interaction):
        cfg = await load()
        try: cfg["dm_options"]["delay"]      = float(self.delay.value or 1.5)
        except: pass
        try: cfg["dm_options"]["max_errors"] = int(self.maxerr.value or 10)
        except: pass
        cfg["dm_options"]["stop_on_error"] = self.stop.value.strip().lower() in ("oui","o","yes","y")
        await save(cfg)
        await _refresh_config(interaction)
        await interaction.followup.send("✅ Options sauvegardées.", ephemeral=True)

import discord
from discord import ui
import asyncio
from db import load, save, set_field, make_embed, authorized
from cv2_helper import (
    respond_v2, followup_v2, edit_v2,
    container, section, separator, text, button, action_row
)


# ── Config Panel ──────────────────────────────────────────────────────────────

async def send_config_panel(interaction: discord.Interaction):
    """Envoie le panel principal en Components V2."""
    cfg = await load()
    nb_tok = len(cfg.get("tokens", []))
    msg    = cfg.get("message", "")
    emb    = cfg.get("embed", {})
    ids    = len(cfg.get("user_ids", []))
    ign    = len(cfg.get("ignore_ids", []))
    delay  = cfg.get("dm_options", {}).get("delay", 1.5)

    tok_val  = f"`{nb_tok}` token(s)" if nb_tok else "*Aucun token*"
    msg_val  = f"```{msg[:50]}{'...' if len(msg) > 50 else ''}```" if msg else "*Aucun message*"
    emb_val  = f"`{emb.get('title','')[:40]}`" if emb.get("enabled") else "*Aucun embed*"

    panel = container(
        text("## ⚙️  Configuration du DMall Ohio\n*Utilisez les boutons ci-dessous pour configurer votre DMall.*"),
        separator(),
        section(f"🤖 **Tokens**\n{tok_val}",          button("➕ Tokens",       "cv_tokens",  style=1)),
        separator(divider=False),
        section(f"📩 **Message**\n{msg_val}",           button("📩 Message",      "cv_message", style=3)),
        separator(divider=False),
        section(f"📝 **Embed**\n{emb_val}",             button("📝 Embed",        "cv_embed",   style=2)),
        separator(),
        section(f"⚙️ **Options de DM** — Délai : **{delay}s**", button("⚙️ Options",   "cv_dmopts",  style=2)),
        separator(divider=False),
        section(f"🎯 **Cibles** — **{ids}** ID(s) ajouté(s)", button("🎯 Cibles",     "cv_targets", style=2)),
        separator(divider=False),
        section(f"🚫 **IDs ignorés** — **{ign}** ignoré(s)", button("🚫 Ignorer",    "cv_ignore",  style=2)),
        separator(),
        section("⭐ **Status** — Définir le statut des bots", button("⭐ Status",     "cv_status",  style=2)),
        separator(divider=False),
        section("🗑️ **Reset** — Réinitialiser la config",    button("🗑️ Reset",     "cv_reset",   style=4)),
        separator(),
        section("🚀 **DMall** — Lancer l'envoi de DMs",      button("🚀 DMall",     "cv_dmall",   style=4)),
        text("-# by Ohio"),
    )
    await respond_v2(interaction, panel)


class ConfigView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _check(self, i: discord.Interaction) -> bool:
        if not await authorized(i.user.id):
            await i.response.send_message("❌ Non autorisé.", ephemeral=True)
            return False
        return True

    @ui.button(label="➕ Tokens",         style=discord.ButtonStyle.primary,   custom_id="cv_tokens",   row=0)
    async def btn_tokens(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        from modals import TokensModal
        await i.response.send_modal(TokensModal())

    @ui.button(label="📩 Message",        style=discord.ButtonStyle.success,   custom_id="cv_message",  row=0)
    async def btn_message(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        await send_message_panel(i)

    @ui.button(label="📝 Embed",          style=discord.ButtonStyle.secondary, custom_id="cv_embed",    row=0)
    async def btn_embed(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        await send_embed_builder_panel(i)

    @ui.button(label="⚙️ Options de DM", style=discord.ButtonStyle.secondary, custom_id="cv_dmopts",   row=1)
    async def btn_dmopts(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        from modals import DMOptionsModal
        await i.response.send_modal(DMOptionsModal())

    @ui.button(label="🎯 Cibles",         style=discord.ButtonStyle.secondary, custom_id="cv_targets",  row=1)
    async def btn_targets(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        await send_targets_panel(i)

    @ui.button(label="🚫 IDs ignorés",   style=discord.ButtonStyle.secondary, custom_id="cv_ignore",   row=1)
    async def btn_ignore(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        from modals import IgnoreIDsModal
        await i.response.send_modal(IgnoreIDsModal())

    @ui.button(label="⭐ Status",         style=discord.ButtonStyle.secondary, custom_id="cv_status",   row=2)
    async def btn_status(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        from modals import StatusModal
        await i.response.send_modal(StatusModal())

    @ui.button(label="🗑️ Reset",         style=discord.ButtonStyle.danger,    custom_id="cv_reset",    row=2)
    async def btn_reset(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        await i.response.send_message("⚠️ Tapez `/reset` pour confirmer la réinitialisation.", ephemeral=True)

    @ui.button(label="🚀 DMall",         style=discord.ButtonStyle.danger,    custom_id="cv_dmall",    row=3)
    async def btn_dmall(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        cfg = await load()
        errs = []
        if not cfg.get("tokens"):   errs.append("❌ Aucun token.")
        if not cfg.get("user_ids"): errs.append("❌ Aucun User ID.")
        if not cfg.get("message") and not cfg.get("embed", {}).get("enabled"):
            errs.append("❌ Il manque un **message** ou un **embed** avant d'envoyer les DMs.")
        if errs:
            await i.response.send_message("\n".join(errs), ephemeral=True)
            return
        await send_dmall_type_panel(i)


# ── Message Panel ─────────────────────────────────────────────────────────────

async def send_message_panel(interaction: discord.Interaction):
    panel = container(
        text("## 📝  Définir le Message à Envoyer\nChoisissez une méthode pour configurer le message :"),
        separator(),
        section(
            "**1️⃣  Message texte simple**\nRédigez un message classique.",
            button("✉️ Saisir le Message", "mp_simple", style=1)
        ),
        separator(divider=False),
        section(
            "**2️⃣  Embed personnalisé**\nCréez un embed avec titre, description, bouton etc.",
            button("🛠️ Embed Builder", "mp_builder", style=3)
        ),
        separator(divider=False),
        section(
            "**📋  Embed via JSON**\nCollez directement votre JSON d'embed.",
            button("📋 Embed JSON", "mp_json", style=2)
        ),
        separator(),
        text("💡 **Astuce** — Variables disponibles :\n`{user}` → mention · `{user.id}` → ID · `{timestamp}` → date/heure"),
        separator(),
        action_row(
            button("👁️ Aperçu",      "mp_preview", style=2),
            button("🗑️ Reset",       "mp_reset",   style=4),
        ),
        text("-# by Ohio"),
    )
    await respond_v2(interaction, panel)


class MessagePanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="✉️ Saisir le Message", style=discord.ButtonStyle.primary,   custom_id="mp_simple",  row=0)
    async def simple(self, i: discord.Interaction, b: ui.Button):
        from modals import SimpleMessageModal
        await i.response.send_modal(SimpleMessageModal())

    @ui.button(label="📋 Embed JSON",        style=discord.ButtonStyle.secondary,  custom_id="mp_json",    row=1)
    async def emb_json(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedJSONModal
        await i.response.send_modal(EmbedJSONModal())

    @ui.button(label="🛠️ Embed Builder",    style=discord.ButtonStyle.success,    custom_id="mp_builder", row=1)
    async def emb_builder(self, i: discord.Interaction, b: ui.Button):
        await send_embed_builder_panel(i)

    @ui.button(label="👁️ Aperçu",          style=discord.ButtonStyle.secondary,  custom_id="mp_preview", row=2)
    async def preview(self, i: discord.Interaction, b: ui.Button):
        cfg = await load()
        emb_cfg = cfg.get("embed", {})
        if emb_cfg.get("enabled"):
            preview = discord.Embed(
                title=emb_cfg.get("title", ""), description=emb_cfg.get("description", ""),
                color=emb_cfg.get("color", 5814783)
            )
            if emb_cfg.get("footer"):        preview.set_footer(text=emb_cfg["footer"])
            if emb_cfg.get("image_url"):     preview.set_image(url=emb_cfg["image_url"])
            if emb_cfg.get("thumbnail_url"): preview.set_thumbnail(url=emb_cfg["thumbnail_url"])
            await i.response.send_message(content="**Aperçu de l'embed :**", embed=preview, ephemeral=True)
        elif cfg.get("message"):
            await i.response.send_message(f"**Aperçu du message :**\n{cfg['message']}", ephemeral=True)
        else:
            await i.response.send_message("❌ Aucun message ni embed défini.", ephemeral=True)

    @ui.button(label="🗑️ Reset Message",    style=discord.ButtonStyle.danger,     custom_id="mp_reset",   row=2)
    async def reset_msg(self, i: discord.Interaction, b: ui.Button):
        await set_field("message", "")
        await set_field("embed", {"enabled": False, "title": "", "description": "",
                                  "color": 5814783, "footer": "", "image_url": "",
                                  "thumbnail_url": "", "button_label": "", "button_url": ""})
        await i.response.send_message("✅ Message réinitialisé.", ephemeral=True)


# ── Embed Builder ─────────────────────────────────────────────────────────────

async def send_embed_builder_panel(interaction: discord.Interaction):
    panel = container(
        text("## 🎨  Créer un Embed\nConfigurez votre embed étape par étape :"),
        separator(),
        section("**1️⃣  Titre**\nDéfinissez le titre de l'embed.",               button("✏️ Titre",           "eb_title",   style=1)),
        separator(divider=False),
        section("**2️⃣  Description**\nDéfinissez la description de l'embed.",   button("📄 Description",     "eb_desc",    style=1)),
        separator(divider=False),
        section("**3️⃣  Couleur & Image**\nDéfinissez la couleur et les images.", button("🎨 Couleur & Image", "eb_color",   style=1)),
        separator(divider=False),
        section("**4️⃣  Thumbnail**\nPetite image affichée en haut à droite.",   button("🖼️ Thumbnail",      "eb_thumb",   style=1)),
        separator(divider=False),
        section("**5️⃣  Bouton lien**\nAjoutez un bouton sous l'embed.",         button("🔗 Bouton",          "eb_btnlink", style=2)),
        separator(),
        action_row(
            button("👁️ Aperçu",  "eb_preview", style=2),
            button("🗑️ Reset",   "eb_reset",   style=4),
            button("✅ Terminer", "eb_done",    style=3),
        ),
        text("-# by Ohio"),
    )
    await respond_v2(interaction, panel)


class EmbedBuilderView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="✏️ Titre",           style=discord.ButtonStyle.primary,   custom_id="eb_title",   row=0)
    async def title(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedTitleModal
        await i.response.send_modal(EmbedTitleModal())

    @ui.button(label="📄 Description",     style=discord.ButtonStyle.primary,   custom_id="eb_desc",    row=0)
    async def desc(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedDescModal
        await i.response.send_modal(EmbedDescModal())

    @ui.button(label="🎨 Couleur & Image", style=discord.ButtonStyle.primary,   custom_id="eb_color",   row=1)
    async def color(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedColorImageModal
        await i.response.send_modal(EmbedColorImageModal())

    @ui.button(label="🖼️ Thumbnail",      style=discord.ButtonStyle.primary,   custom_id="eb_thumb",   row=1)
    async def thumb(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedThumbnailModal
        await i.response.send_modal(EmbedThumbnailModal())

    @ui.button(label="🔗 Bouton lien",    style=discord.ButtonStyle.secondary,  custom_id="eb_btnlink", row=2)
    async def btn_link(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedButtonModal
        await i.response.send_modal(EmbedButtonModal())

    @ui.button(label="👁️ Aperçu",        style=discord.ButtonStyle.secondary,  custom_id="eb_preview", row=3)
    async def preview(self, i: discord.Interaction, b: ui.Button):
        cfg = await load()
        emb_cfg = cfg.get("embed", {})
        preview = discord.Embed(
            title=emb_cfg.get("title", "(sans titre)"),
            description=emb_cfg.get("description", ""),
            color=emb_cfg.get("color", 5814783)
        )
        if emb_cfg.get("footer"):        preview.set_footer(text=emb_cfg["footer"])
        if emb_cfg.get("image_url"):     preview.set_image(url=emb_cfg["image_url"])
        if emb_cfg.get("thumbnail_url"): preview.set_thumbnail(url=emb_cfg["thumbnail_url"])
        await i.response.send_message(embed=preview, ephemeral=True)

    @ui.button(label="🗑️ Reset",         style=discord.ButtonStyle.danger,     custom_id="eb_reset",   row=3)
    async def reset(self, i: discord.Interaction, b: ui.Button):
        await set_field("embed", {"enabled": False, "title": "", "description": "",
                                  "color": 5814783, "footer": "", "image_url": "",
                                  "thumbnail_url": "", "button_label": "", "button_url": ""})
        await i.response.send_message("✅ Embed réinitialisé.", ephemeral=True)

    @ui.button(label="✅ Terminer",       style=discord.ButtonStyle.success,    custom_id="eb_done",    row=3)
    async def done(self, i: discord.Interaction, b: ui.Button):
        await i.response.send_message("✅ Embed sauvegardé.", ephemeral=True)


# ── Target Method View ────────────────────────────────────────────────────────

async def send_targets_panel(interaction: discord.Interaction):
    panel = container(
        text("## ⚙️  Options de DM\nChoisissez une option pour récupérer les membres :"),
        separator(),
        section("**1️⃣  Ajouter des IDs**\nAjoutez un ou plusieurs IDs manuellement.",              button("➕ Ajouter des IDs",    "tm_ids",     style=1)),
        separator(divider=False),
        section("**2️⃣  Fetch des membres**\nRécupère tous les membres (filtrez par statut).",       button("👥 Membres",            "tm_members", style=1)),
        separator(divider=False),
        section("**3️⃣  Fetch par rôles**\nRécupère les membres ayant certains rôles.",              button("🎭 Membres par Rôles",  "tm_roles",   style=1)),
        separator(divider=False),
        section("**4️⃣  Fetch Vocal**\nRécupère les membres en vocal.",                              button("🔊 Membres Vocal",      "tm_vocal",   style=1)),
        separator(divider=False),
        section("**5️⃣  Autres**\nAffiche d'autres options.",                                        button("⚙️ Autres",            "tm_other",   style=2)),
        text("-# by Ohio"),
    )
    await respond_v2(interaction, panel)


class TargetMethodView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="➕ Ajouter des IDs",   style=discord.ButtonStyle.primary,   custom_id="tm_ids",    row=0)
    async def manual_ids(self, i: discord.Interaction, b: ui.Button):
        from modals import UserIDsModal
        await i.response.send_modal(UserIDsModal())

    @ui.button(label="👥 Membres",           style=discord.ButtonStyle.primary,   custom_id="tm_members", row=0)
    async def members(self, i: discord.Interaction, b: ui.Button):
        if not i.guild:
            await i.response.send_message("❌ Doit être utilisé dans un serveur.", ephemeral=True); return
        await i.response.send_message(
            embed=discord.Embed(title="👥 Fetch des membres", description="Sélectionnez les statuts à inclure :", color=0x5865F2),
            view=StatusFilterView(i.guild), ephemeral=False
        )

    @ui.button(label="🎭 Membres par Rôles", style=discord.ButtonStyle.primary,   custom_id="tm_roles",  row=1)
    async def by_roles(self, i: discord.Interaction, b: ui.Button):
        if not i.guild:
            await i.response.send_message("❌ Doit être utilisé dans un serveur.", ephemeral=True); return
        await i.response.send_message(
            embed=discord.Embed(title="🎭 Fetch par rôles", description="Sélectionnez les rôles :", color=0x5865F2),
            view=RoleFetchView(i.guild), ephemeral=False
        )

    @ui.button(label="🔊 Membres Vocal",     style=discord.ButtonStyle.primary,   custom_id="tm_vocal",  row=1)
    async def by_vocal(self, i: discord.Interaction, b: ui.Button):
        if not i.guild:
            await i.response.send_message("❌ Doit être utilisé dans un serveur.", ephemeral=True); return
        await i.response.defer(ephemeral=True)
        members_ids = []
        for vc in i.guild.voice_channels:
            for m in vc.members:
                if not m.bot and m.id not in members_ids:
                    members_ids.append(m.id)
        cfg = await load()
        added = 0
        for uid in members_ids:
            if uid not in cfg["user_ids"]: cfg["user_ids"].append(uid); added += 1
        await save(cfg)
        await i.followup.send(f"✅ **{added}** membres vocaux récupérés. Total : **{len(cfg['user_ids'])}**", ephemeral=True)

    @ui.button(label="⚙️ Autres",           style=discord.ButtonStyle.secondary, custom_id="tm_other",  row=2)
    async def other(self, i: discord.Interaction, b: ui.Button):
        await i.response.send_message(
            embed=discord.Embed(title="⚙️ Autres options", color=0x5865F2)
            .add_field(name="🗑️ Vider les IDs",   value="Utilisez `/clearids`",                             inline=False)
            .add_field(name="🚫 IDs à ignorer",   value="Utilisez le bouton 🚫 sur le panel principal.",    inline=False)
            .set_footer(text="by Ohio"),
            ephemeral=True
        )


# ── Status Filter View ────────────────────────────────────────────────────────

STATUS_OPTS = [
    discord.SelectOption(label="Online",  value="online",  emoji="🟢"),
    discord.SelectOption(label="Idle",    value="idle",    emoji="🟡"),
    discord.SelectOption(label="DND",     value="dnd",     emoji="🔴"),
    discord.SelectOption(label="Offline", value="offline", emoji="⚫"),
]

class StatusSelect(ui.Select):
    def __init__(self, guild: discord.Guild):
        super().__init__(placeholder="Sélectionnez les statuts à inclure",
                         min_values=1, max_values=4, options=STATUS_OPTS, custom_id="ss_select")
        self.guild = guild

    async def callback(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        wanted = set(self.values)
        ids = []
        async for m in self.guild.fetch_members(limit=None):
            if m.bot: continue
            st = str(getattr(m, "status", "offline"))
            if st in wanted or not wanted:
                ids.append(m.id)
        cfg = await load()
        added = 0
        for uid in ids:
            if uid not in cfg["user_ids"]: cfg["user_ids"].append(uid); added += 1
        await save(cfg)
        await i.followup.send(f"✅ **{added}** membres récupérés. Total : **{len(cfg['user_ids'])} ID**", ephemeral=True)

class StatusFilterView(ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=120)
        self.add_item(StatusSelect(guild))

    @ui.button(label="✅ Tous les membres", style=discord.ButtonStyle.success, custom_id="sf_all", row=1)
    async def all_members(self, i: discord.Interaction, b: ui.Button):
        await i.response.defer(ephemeral=True)
        cfg = await load()
        added = 0
        async for m in i.guild.fetch_members(limit=None):
            if not m.bot and m.id not in cfg["user_ids"]:
                cfg["user_ids"].append(m.id); added += 1
        await save(cfg)
        await i.followup.send(f"✅ **{added}** membres récupérés. Total : **{len(cfg['user_ids'])} ID**", ephemeral=True)


# ── Role Fetch View ───────────────────────────────────────────────────────────

class RoleSelect(ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Sélectionnez un ou plusieurs rôles",
                         min_values=1, max_values=10, custom_id="rs_select")

    async def callback(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        cfg = await load()
        added = 0
        for role in self.values:
            for m in role.members:
                if not m.bot and m.id not in cfg["user_ids"]:
                    cfg["user_ids"].append(m.id); added += 1
        await save(cfg)
        names = ", ".join(r.name for r in self.values)
        await i.followup.send(f"✅ **{added}** membres récupérés depuis : {names}\nTotal : **{len(cfg['user_ids'])} ID**", ephemeral=True)

class RoleFetchView(ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=120)
        self.add_item(RoleSelect())


# ── DMall Type View ───────────────────────────────────────────────────────────

async def send_dmall_type_panel(interaction: discord.Interaction):
    cfg = await load()
    nb_tok = len(cfg.get("tokens", []))
    nb_ids = len(cfg.get("user_ids", []))
    panel = container(
        text(f"## 🚀  Choix du type de DMall\n`{nb_tok}` token(s) → `{nb_ids}` cible(s)"),
        separator(),
        section("**1️⃣  DMall Normal**\nEnvoi classique multi-bots en parallèle.",               button("DMall Normal",    "dt_normal", style=1)),
        separator(divider=False),
        section("**2️⃣  DMall Eco ⭐**\n1 bot à la fois, switch automatique si banni.",          button("DMall Eco ⭐",   "dt_eco",    style=4)),
        separator(divider=False),
        section("**3️⃣  DMall Custom ⭐**\nDélai personnalisé entre chaque message envoyé.",     button("DMall Custom ⭐", "dt_custom", style=4)),
        text("-# by Ohio"),
    )
    await respond_v2(interaction, panel)


class DMallTypeView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="DMall Normal",    style=discord.ButtonStyle.primary, custom_id="dt_normal", row=0)
    async def normal(self, i: discord.Interaction, b: ui.Button):
        from dmall import run_normal
        cfg = await load()
        await i.response.defer()
        await i.followup.send(
            f"🚀 **DMall Normal** lancé — `{len(cfg['tokens'])}` token(s) → `{len(cfg['user_ids'])}` cibles\n"
            f"*(Les bots vont se connecter et commencer l'envoi...)*"
        )
        asyncio.create_task(run_normal(cfg, i))

    @ui.button(label="DMall Eco ⭐",   style=discord.ButtonStyle.danger,   custom_id="dt_eco",    row=0)
    async def eco(self, i: discord.Interaction, b: ui.Button):
        from dmall import run_eco
        cfg = await load()
        await i.response.defer()
        await i.followup.send(
            f"🚀 **DMall Eco** lancé — `{len(cfg['tokens'])}` token(s) → `{len(cfg['user_ids'])}` cibles\n"
            f"*(Mode Éco : 1 bot à la fois, switch automatique si banni)*"
        )
        asyncio.create_task(run_eco(cfg, i))

    @ui.button(label="DMall Custom ⭐", style=discord.ButtonStyle.danger,   custom_id="dt_custom", row=0)
    async def custom(self, i: discord.Interaction, b: ui.Button):
        from modals import CustomDelayModal
        cfg = await load()
        await i.response.send_modal(CustomDelayModal(cfg))

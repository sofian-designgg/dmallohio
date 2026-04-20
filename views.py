import discord
from discord import ui
import asyncio
from db import load, save, set_field, make_embed, authorized


# ── Config Panel ──────────────────────────────────────────────────────────────

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
        await i.response.send_message(embed=_message_panel_embed(), view=MessagePanelView(), ephemeral=False)

    @ui.button(label="⚙️ Options de DM", style=discord.ButtonStyle.secondary, custom_id="cv_dmopts",   row=1)
    async def btn_dmopts(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        from modals import DMOptionsModal
        await i.response.send_modal(DMOptionsModal())

    @ui.button(label="🎯 Cibles",         style=discord.ButtonStyle.secondary, custom_id="cv_targets",  row=1)
    async def btn_targets(self, i: discord.Interaction, b: ui.Button):
        if not await self._check(i): return
        await i.response.send_message(embed=_targets_embed(), view=TargetMethodView(i.guild), ephemeral=False)

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
        await i.response.send_message(embed=_dmall_type_embed(), view=DMallTypeView(cfg), ephemeral=False)


# ── Message Panel ─────────────────────────────────────────────────────────────

def _message_panel_embed() -> discord.Embed:
    e = discord.Embed(
        title="📝  Définir le Message à Envoyer",
        description="Choisissez une méthode pour configurer le message qui sera envoyé aux membres :",
        color=0x5865F2
    )
    e.add_field(name="1️⃣  Message texte simple",
                value="Rédigez un message classique.", inline=False)
    e.add_field(name="2️⃣  Embed personnalisé",
                value="Créez un embed avec titre, description, bouton etc.", inline=False)
    e.add_field(name="💡 Astuce",
                value="`{user}` → mention du membre\n`{user.id}` → id du membre\n`{timestamp}` → date/heure actuel",
                inline=False)
    e.set_footer(text="by Ohio")
    return e

class MessagePanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @ui.button(label="✉️ Saisir le Message", style=discord.ButtonStyle.primary,   custom_id="mp_simple", row=0)
    async def simple(self, i: discord.Interaction, b: ui.Button):
        from modals import SimpleMessageModal
        await i.response.send_modal(SimpleMessageModal())

    @ui.button(label="📋 Embed JSON",       style=discord.ButtonStyle.secondary,  custom_id="mp_json",   row=1)
    async def emb_json(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedJSONModal
        await i.response.send_modal(EmbedJSONModal())

    @ui.button(label="🛠️ Embed Builder",   style=discord.ButtonStyle.success,    custom_id="mp_builder",row=1)
    async def emb_builder(self, i: discord.Interaction, b: ui.Button):
        await i.response.edit_message(embed=_embed_builder_embed(), view=EmbedBuilderView())

    @ui.button(label="👁️ Aperçu",         style=discord.ButtonStyle.secondary,  custom_id="mp_preview", row=2)
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

    @ui.button(label="🗑️ Reset Message",   style=discord.ButtonStyle.danger,     custom_id="mp_reset",  row=2)
    async def reset_msg(self, i: discord.Interaction, b: ui.Button):
        await set_field("message", "")
        await set_field("embed", {"enabled": False, "title": "", "description": "",
                                  "color": 5814783, "footer": "", "image_url": "",
                                  "thumbnail_url": "", "button_label": "", "button_url": ""})
        await i.response.edit_message(embed=_message_panel_embed(), view=MessagePanelView())
        await i.followup.send("✅ Message réinitialisé.", ephemeral=True)


# ── Embed Builder ─────────────────────────────────────────────────────────────

def _embed_builder_embed() -> discord.Embed:
    e = discord.Embed(title="🎨  Créer un Embed",
                      description="Configurez votre embed étape par étape :",
                      color=0x5865F2)
    e.add_field(name="1️⃣  Titre",          value="Définissez le titre de l'embed.",            inline=False)
    e.add_field(name="2️⃣  Description",    value="Définissez la description de l'embed.",      inline=False)
    e.add_field(name="3️⃣  Couleur & Image",value="Définissez la couleur et les images.",        inline=False)
    e.add_field(name="4️⃣  Thumbnail",      value="Petite image affichée en haut à droite.",     inline=False)
    e.set_footer(text="by Ohio")
    return e

class EmbedBuilderView(ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @ui.button(label="✏️ Titre",           style=discord.ButtonStyle.primary,   custom_id="eb_title",  row=0)
    async def title(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedTitleModal
        await i.response.send_modal(EmbedTitleModal())

    @ui.button(label="📄 Description",     style=discord.ButtonStyle.primary,   custom_id="eb_desc",   row=0)
    async def desc(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedDescModal
        await i.response.send_modal(EmbedDescModal())

    @ui.button(label="🎨 Couleur & Image", style=discord.ButtonStyle.primary,   custom_id="eb_color",  row=1)
    async def color(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedColorImageModal
        await i.response.send_modal(EmbedColorImageModal())

    @ui.button(label="🖼️ Thumbnail",      style=discord.ButtonStyle.primary,   custom_id="eb_thumb",  row=1)
    async def thumb(self, i: discord.Interaction, b: ui.Button):
        from modals import EmbedThumbnailModal
        await i.response.send_modal(EmbedThumbnailModal())

    @ui.button(label="👁️ Aperçu",        style=discord.ButtonStyle.secondary, custom_id="eb_preview",row=2)
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

    @ui.button(label="✅ Terminer",       style=discord.ButtonStyle.success,   custom_id="eb_done",   row=2)
    async def done(self, i: discord.Interaction, b: ui.Button):
        await i.response.edit_message(embed=await make_embed(), view=ConfigView())


# ── Target Method View ────────────────────────────────────────────────────────

def _targets_embed() -> discord.Embed:
    e = discord.Embed(title="⚙️  Options de DM",
                      description="Choisissez une option pour récupérer les membres à qui envoyer des messages :",
                      color=0x5865F2)
    e.add_field(name="1️⃣  Ajouter des IDs",   value="Permet d'ajouter un ou plusieurs IDs manuellement.",                         inline=False)
    e.add_field(name="2️⃣  Fetch des membres", value="Récupère tous les membres du serveur (vous pouvez choisir le statut).",       inline=False)
    e.add_field(name="3️⃣  Fetch par rôles",   value="Récupère les membres ayant certains rôles spécifiés.",                        inline=False)
    e.add_field(name="4️⃣  Fetch Vocal",       value="Récupère sur les membres en vocal ou ceux pas en vocal.",                     inline=False)
    e.add_field(name="5️⃣  Autres",            value="Affiche d'autres options.",                                                   inline=False)
    e.set_footer(text="by Ohio")
    return e

class TargetMethodView(ui.View):
    def __init__(self, guild: discord.Guild | None):
        super().__init__(timeout=120)
        self.guild = guild

    @ui.button(label="➕ Ajouter des IDs",   style=discord.ButtonStyle.primary,   custom_id="tm_ids",    row=0)
    async def manual_ids(self, i: discord.Interaction, b: ui.Button):
        from modals import UserIDsModal
        await i.response.send_modal(UserIDsModal())

    @ui.button(label="👥 Membres",           style=discord.ButtonStyle.primary,   custom_id="tm_members",row=0)
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
        added = sum(1 for uid in members_ids if uid not in cfg["user_ids"] or not cfg["user_ids"].append(uid))
        added = 0
        for uid in members_ids:
            if uid not in cfg["user_ids"]: cfg["user_ids"].append(uid); added += 1
        await save(cfg)
        await i.followup.send(f"✅ **{added}** membres vocaux récupérés. Total : **{len(cfg['user_ids'])}**", ephemeral=True)

    @ui.button(label="⚙️ Autres",           style=discord.ButtonStyle.secondary, custom_id="tm_other",  row=2)
    async def other(self, i: discord.Interaction, b: ui.Button):
        await i.response.send_message(
            embed=discord.Embed(title="⚙️ Autres options", color=0x5865F2)
            .add_field(name="🗑️ Vider les IDs",     value="Utilisez `/clearids`",     inline=False)
            .add_field(name="🚫 IDs à ignorer",     value="Utilisez le bouton 🚫 sur le panel principal.", inline=False)
            .set_footer(text="by Ohio"),
            ephemeral=True
        )


# ── Status Filter View ────────────────────────────────────────────────────────

STATUS_OPTS = [
    discord.SelectOption(label="Online",   value="online",  emoji="🟢"),
    discord.SelectOption(label="Idle",     value="idle",    emoji="🟡"),
    discord.SelectOption(label="DND",      value="dnd",     emoji="🔴"),
    discord.SelectOption(label="Offline",  value="offline", emoji="⚫"),
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

def _dmall_type_embed() -> discord.Embed:
    e = discord.Embed(title="🚀  Choix du type de DMall",
                      description="Choisissez une méthode de DMall :", color=0x5865F2)
    e.add_field(name="1️⃣  DMall Normal",  value="Envoi classique.", inline=False)
    e.add_field(name="2️⃣  DMall Eco ⭐",  value="Utilise 1 bot à la fois, passe au suivant si banni.", inline=False)
    e.add_field(name="3️⃣  DMall Custom ⭐", value="Envoi avec un délai personnalisé entre chaque message.", inline=False)
    e.set_footer(text="by Ohio")
    return e

class DMallTypeView(ui.View):
    def __init__(self, cfg: dict):
        super().__init__(timeout=120)
        self.cfg = cfg

    @ui.button(label="DMall Normal",    style=discord.ButtonStyle.primary, custom_id="dt_normal", row=0)
    async def normal(self, i: discord.Interaction, b: ui.Button):
        from dmall import run_normal
        await i.response.send_message(f"🚀 **DMall Normal** lancé ! `{len(self.cfg['tokens'])}` token(s) → `{len(self.cfg['user_ids'])}` cibles", ephemeral=True)
        asyncio.create_task(run_normal(self.cfg, i))

    @ui.button(label="DMall Eco ⭐",   style=discord.ButtonStyle.danger,   custom_id="dt_eco",    row=0)
    async def eco(self, i: discord.Interaction, b: ui.Button):
        from dmall import run_eco
        await i.response.send_message(f"🚀 **DMall Eco** lancé !", ephemeral=True)
        asyncio.create_task(run_eco(self.cfg, i))

    @ui.button(label="DMall Custom ⭐", style=discord.ButtonStyle.danger,   custom_id="dt_custom", row=0)
    async def custom(self, i: discord.Interaction, b: ui.Button):
        from modals import CustomDelayModal
        await i.response.send_modal(CustomDelayModal(self.cfg))

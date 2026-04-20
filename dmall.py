import discord
import asyncio
from datetime import datetime

def _resolve_vars(text: str, user: discord.User) -> str:
    """Replace {user}, {user.id}, {timestamp} variables."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    return text.replace("{user}", user.mention).replace("{user.id}", str(user.id)).replace("{timestamp}", now)

async def _send_dm(client: discord.Client, uid: int, cfg: dict):
    user = await client.fetch_user(uid)
    dm   = await user.create_dm()
    msg  = cfg.get("message", "")
    emb_cfg = cfg.get("embed", {})

    embed = None
    if emb_cfg.get("enabled"):
        embed = discord.Embed(
            title=emb_cfg.get("title", ""),
            description=_resolve_vars(emb_cfg.get("description", ""), user),
            color=emb_cfg.get("color", 5814783)
        )
        if emb_cfg.get("footer"):        embed.set_footer(text=emb_cfg["footer"])
        if emb_cfg.get("image_url"):     embed.set_image(url=emb_cfg["image_url"])
        if emb_cfg.get("thumbnail_url"): embed.set_thumbnail(url=emb_cfg["thumbnail_url"])

    content = _resolve_vars(msg, user) if msg else None

    view = None
    if emb_cfg.get("button_label") and emb_cfg.get("button_url"):
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label=emb_cfg["button_label"], url=emb_cfg["button_url"]))

    await dm.send(content=content, embed=embed, view=view)

# ── Progress embed helpers ────────────────────────────────────────────────────

def _progress_embed(sent: int, errors: int, total: int, token_idx: int, total_tokens: int, status: str = "🔄 En cours...") -> discord.Embed:
    pct = int((sent + errors) / total * 100) if total > 0 else 0
    bar_filled = pct // 10
    bar = "█" * bar_filled + "░" * (10 - bar_filled)
    embed = discord.Embed(
        title="📨 DMall — Progression",
        description=f"**Statut :** {status}",
        color=0x5865F2
    )
    embed.add_field(name="📊 Progression",   value=f"`[{bar}]` **{pct}%**\n`{sent + errors}/{total}` traités", inline=False)
    embed.add_field(name="✅ DMs envoyés",   value=f"**{sent}**",                       inline=True)
    embed.add_field(name="❌ Erreurs",       value=f"**{errors}**",                     inline=True)
    embed.add_field(name="🤖 Token actif",   value=f"**{token_idx}/{total_tokens}**",   inline=True)
    embed.set_footer(text=f"MultiDmall by SofianDev • {datetime.now().strftime('%H:%M:%S')}")
    return embed

async def _safe_edit(msg: discord.Message, embed: discord.Embed):
    try:
        await msg.edit(embed=embed)
    except Exception:
        pass

async def _notify(interaction: discord.Interaction, embed: discord.Embed):
    """Send a followup notification silently."""
    try:
        await interaction.followup.send(embed=embed, silent=True)
    except Exception:
        pass

# ── Normal mode: all tokens send in parallel ──────────────────────────────────

async def _token_worker(token: str, cfg: dict, idx: int,
                        interaction: discord.Interaction,
                        progress_msg: discord.Message,
                        shared: dict, lock: asyncio.Lock) -> dict:
    client = discord.Client()
    res = {"sent": 0, "errors": 0}
    ignore = set(cfg.get("ignore_ids", []))
    delay  = cfg["dm_options"]["delay"]
    max_e  = cfg["dm_options"]["max_errors"]
    total  = len(cfg.get("user_ids", []))
    total_tokens = len(cfg.get("tokens", []))
    connected = False  # track if on_ready actually fired

    @client.event
    async def on_ready():
        nonlocal res, connected
        connected = True
        async with lock:
            shared["connected"] += 1

        # ✅ Notify Discord: bot is now online
        connect_embed = discord.Embed(
            title="🟢 Bot connecté",
            description=f"**Bot {idx+1}** est en ligne : `{client.user}` (`{client.user.id}`)\n"
                        f"Début de l'envoi vers **{len(cfg.get('user_ids', []))}** cibles...",
            color=0x57F287
        )
        connect_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
        await _notify(interaction, connect_embed)

        if cfg.get("status"):
            await client.change_presence(activity=discord.Game(name=cfg["status"]))

        for uid in cfg.get("user_ids", []):
            if uid in ignore: continue
            try:
                await _send_dm(client, uid, cfg)
                res["sent"] += 1
                async with lock:
                    shared["sent"] += 1
                print(f"[Bot {idx+1}] ✅ → {uid}")
            except discord.Forbidden:
                res["errors"] += 1
                async with lock:
                    shared["errors"] += 1
                print(f"[Bot {idx+1}] ⚠️ Bloqué/banni → {uid}")
            except Exception as e:
                res["errors"] += 1
                async with lock:
                    shared["errors"] += 1
                print(f"[Bot {idx+1}] ❌ {uid}: {e}")

            # Update progress embed every 5 messages
            async with lock:
                shared["processed"] += 1
                if shared["processed"] % 5 == 0 or shared["processed"] == total:
                    embed = _progress_embed(
                        shared["sent"], shared["errors"],
                        total * total_tokens, idx + 1, total_tokens
                    )
                    await _safe_edit(progress_msg, embed)

            if res["errors"] >= max_e and cfg["dm_options"]["stop_on_error"]:
                print(f"[Bot {idx+1}] 🛑 Arrêt — trop d'erreurs.")
                break
            await asyncio.sleep(delay)
        await client.close()

    try:
        await client.start(token, bot=True)   # bot=True : compte d'application Discord
    except discord.LoginFailure as e:
        async with lock:
            shared["banned_tokens"].append(idx + 1)
        print(f"[Bot {idx+1}] 🚫 TOKEN INVALIDE : {e}")
        err_embed = discord.Embed(
            title="🔴 Token invalide",
            description=f"**Bot {idx+1}** — token refusé par Discord.\n"
                        f"> `{e}`\n\n*Vérifiez que le token est correct et que le bot n'est pas banni.*",
            color=0xED4245
        )
        err_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
        await _notify(interaction, err_embed)
        res["errors"] += 1
    except discord.HTTPException as e:
        async with lock:
            shared["banned_tokens"].append(idx + 1)
        print(f"[Bot {idx+1}] 🚫 ERREUR HTTP : {e}")
        err_embed = discord.Embed(
            title="🔴 Erreur de connexion (HTTP)",
            description=f"**Bot {idx+1}** — Discord a rejeté la connexion.\n"
                        f"> Code `{e.status}` : `{e.text}`",
            color=0xED4245
        )
        err_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
        await _notify(interaction, err_embed)
        res["errors"] += 1
    except Exception as e:
        print(f"[Bot {idx+1}] ❌ Erreur inattendue : {e}")
        err_embed = discord.Embed(
            title="🔴 Erreur inattendue",
            description=f"**Bot {idx+1}** a planté avant de se connecter.\n> `{type(e).__name__}: {e}`",
            color=0xED4245
        )
        err_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
        await _notify(interaction, err_embed)
        res["errors"] += 1

    if not connected:
        async with lock:
            if idx + 1 not in shared["banned_tokens"]:
                shared["banned_tokens"].append(idx + 1)

    return res

async def run_normal(cfg: dict, interaction: discord.Interaction):
    total_tokens = len(cfg.get("tokens", []))
    total_ids    = len(cfg.get("user_ids", []))
    shared = {"sent": 0, "errors": 0, "processed": 0, "banned_tokens": [], "connected": 0}
    lock   = asyncio.Lock()

    # Initial progress embed
    init_embed = _progress_embed(0, 0, total_ids * total_tokens, 1, total_tokens, "🚀 Connexion des bots...")
    progress_msg = await interaction.followup.send(embed=init_embed)

    results = await asyncio.gather(*[
        _token_worker(t, cfg, i, interaction, progress_msg, shared, lock)
        for i, t in enumerate(cfg["tokens"])
    ])

    # ❌ Abort if no bot connected at all
    if shared["connected"] == 0:
        abort_embed = discord.Embed(
            title="❌ DMall annulé — Aucun bot connecté",
            description=f"Aucun des **{total_tokens}** bot(s) n'a pu se connecter.\n"
                        f"Vérifiez vos tokens dans le panel de configuration.",
            color=0xED4245
        )
        abort_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
        await _safe_edit(progress_msg, abort_embed)
        return

    await _send_result(interaction, results, cfg, progress_msg, shared["banned_tokens"])

# ── Eco mode: one token at a time, switch on ban ──────────────────────────────

async def run_eco(cfg: dict, interaction: discord.Interaction):
    ignore   = set(cfg.get("ignore_ids", []))
    delay    = cfg["dm_options"]["delay"]
    user_ids = [u for u in cfg.get("user_ids", []) if u not in ignore]
    tokens   = cfg.get("tokens", [])
    total_sent, total_errors = 0, 0
    idx = 0
    banned_tokens = []
    total_users = len(user_ids)
    total_tokens = len(tokens)

    # Initial progress embed
    init_embed = _progress_embed(0, 0, total_users, 1, total_tokens, "🚀 Connexion du premier bot (mode Éco)...")
    progress_msg = await interaction.followup.send(embed=init_embed)

    while user_ids and idx < len(tokens):
        token = tokens[idx]
        client = discord.Client()
        remaining = []
        token_banned = False

        @client.event
        async def on_ready(token_idx=idx):
            nonlocal total_sent, total_errors, token_banned

            # ✅ Notify Discord: bot is now online
            connect_embed = discord.Embed(
                title="🟢 Bot connecté",
                description=f"**Bot {token_idx+1}** est en ligne : `{client.user}` (`{client.user.id}`)\n"
                            f"Reprise de l'envoi — **{len(user_ids)}** cibles restantes...",
                color=0x57F287
            )
            connect_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
            await _notify(interaction, connect_embed)

            if cfg.get("status"):
                await client.change_presence(activity=discord.Game(name=cfg["status"]))

            for uid in user_ids:
                try:
                    await _send_dm(client, uid, cfg)
                    total_sent += 1
                    print(f"[Eco Bot {token_idx+1}] ✅ → {uid}")
                except discord.Forbidden:
                    remaining.append(uid)
                    total_errors += 1
                    token_banned = True
                    print(f"[Eco Bot {token_idx+1}] 🚫 BANNI — switch vers Bot {token_idx+2}")
                    ban_embed = discord.Embed(
                        title="🚫 Bot banni — Switch automatique",
                        description=f"Le **Bot {token_idx+1}** (`{client.user}`) a été banni/bloqué.\n"
                                    f"➡️ Passage au **Bot {token_idx+2}** avec `{len(remaining)}` cibles restantes...",
                        color=0xED4245
                    )
                    ban_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
                    await _notify(interaction, ban_embed)
                    await client.close(); return
                except Exception as e:
                    total_errors += 1
                    print(f"[Eco Bot {token_idx+1}] ❌ {uid}: {e}")

                # Update progress every 5 DMs
                if (total_sent + total_errors) % 5 == 0 or (total_sent + total_errors) == total_users:
                    embed = _progress_embed(
                        total_sent, total_errors, total_users,
                        token_idx + 1, total_tokens,
                        f"🔄 En cours — Bot {token_idx+1} (`{client.user}`)"
                    )
                    await _safe_edit(progress_msg, embed)

                await asyncio.sleep(delay)
            await client.close()

        try:
            await client.start(token, bot=True)   # bot=True : compte d'application Discord
        except discord.LoginFailure as e:
            banned_tokens.append(idx + 1)
            print(f"[Eco Bot {idx+1}] 🚫 TOKEN INVALIDE : {e}")
            err_embed = discord.Embed(
                title="🔴 Token invalide",
                description=f"**Bot {idx+1}** — token refusé par Discord.\n"
                            f"> `{e}`\n\n*Vérifiez le token ou remplacez-le dans le panel.*",
                color=0xED4245
            )
            err_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
            await _notify(interaction, err_embed)
            idx += 1; continue
        except discord.HTTPException as e:
            banned_tokens.append(idx + 1)
            print(f"[Eco Bot {idx+1}] 🚫 ERREUR HTTP : {e}")
            err_embed = discord.Embed(
                title="🔴 Erreur de connexion (HTTP)",
                description=f"**Bot {idx+1}** — Discord a rejeté la connexion.\n"
                            f"> Code `{e.status}` : `{e.text}`",
                color=0xED4245
            )
            err_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
            await _notify(interaction, err_embed)
            idx += 1; continue
        except Exception as e:
            banned_tokens.append(idx + 1)
            print(f"[Eco Bot {idx+1}] ❌ Erreur inattendue : {e}")
            err_embed = discord.Embed(
                title="🔴 Erreur inattendue",
                description=f"**Bot {idx+1}** a planté avant de se connecter.\n> `{type(e).__name__}: {e}`",
                color=0xED4245
            )
            err_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
            await _notify(interaction, err_embed)
            idx += 1; continue

        if remaining or token_banned:
            user_ids = remaining
            idx += 1
        else:
            break

    # ❌ Abort if no DMs were sent at all (no bot connected)
    if total_sent == 0 and len(banned_tokens) == total_tokens:
        abort_embed = discord.Embed(
            title="❌ DMall annulé — Aucun bot connecté",
            description=f"Aucun des **{total_tokens}** bot(s) n'a pu se connecter.\n"
                        f"Vérifiez vos tokens dans le panel de configuration.",
            color=0xED4245
        )
        abort_embed.set_footer(text=f"MultiDmall • {datetime.now().strftime('%H:%M:%S')}")
        await _safe_edit(progress_msg, abort_embed)
        return

    res = [{"sent": total_sent, "errors": total_errors}]
    await _send_result(interaction, res, cfg, progress_msg, banned_tokens)

# ── Result embed ──────────────────────────────────────────────────────────────

async def _send_result(interaction: discord.Interaction, results: list, cfg: dict,
                       progress_msg: discord.Message = None, banned_tokens: list = None):
    sent   = sum(r["sent"]   for r in results)
    errors = sum(r["errors"] for r in results)

    # Update progress message to "Terminé"
    if progress_msg:
        total = len(cfg.get("user_ids", [])) * max(1, len(cfg.get("tokens", [])))
        done_embed = _progress_embed(sent, errors, total, len(cfg["tokens"]), len(cfg["tokens"]), "✅ Terminé !")
        done_embed.color = 0x57F287 if errors == 0 else 0xFEE75C
        await _safe_edit(progress_msg, done_embed)

    # Final result embed
    embed = discord.Embed(
        title="🏁 DMall Terminé",
        color=0x57F287 if errors == 0 else 0xED4245
    )
    embed.add_field(name="✅ DMs envoyés",     value=f"**{sent}**",               inline=True)
    embed.add_field(name="❌ Erreurs",         value=f"**{errors}**",             inline=True)
    embed.add_field(name="🤖 Bots utilisés",  value=f"**{len(cfg['tokens'])}**", inline=True)

    if banned_tokens:
        embed.add_field(
            name="🚫 Bots bannis/invalides",
            value="\n".join(f"• Bot **{t}**" for t in banned_tokens),
            inline=False
        )

    embed.set_footer(text=f"MultiDmall by SofianDev • {datetime.now().strftime('%H:%M:%S')}")
    try:
        await interaction.followup.send(embed=embed)
    except Exception:
        pass

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

# ── Normal mode: all tokens send in parallel ──────────────────────────────────

async def _token_worker(token: str, cfg: dict, idx: int) -> dict:
    client = discord.Client()
    res = {"sent": 0, "errors": 0}
    ignore = set(cfg.get("ignore_ids", []))
    delay  = cfg["dm_options"]["delay"]
    max_e  = cfg["dm_options"]["max_errors"]

    @client.event
    async def on_ready():
        if cfg.get("status"):
            await client.change_presence(activity=discord.Game(name=cfg["status"]))
        for uid in cfg.get("user_ids", []):
            if uid in ignore: continue
            try:
                await _send_dm(client, uid, cfg)
                res["sent"] += 1
                print(f"[Token {idx+1}] ✅ → {uid}")
            except discord.Forbidden:
                res["errors"] += 1
                print(f"[Token {idx+1}] ❌ Fermé : {uid}")
            except Exception as e:
                res["errors"] += 1
                print(f"[Token {idx+1}] ❌ {uid}: {e}")
            if res["errors"] >= max_e and cfg["dm_options"]["stop_on_error"]:
                print(f"[Token {idx+1}] 🛑 Arrêt."); break
            await asyncio.sleep(delay)
        await client.close()

    try:
        await client.start(token, bot=False)
    except Exception as e:
        print(f"[Token {idx+1}] ❌ Invalide: {e}"); res["errors"] += 1
    return res

async def run_normal(cfg: dict, interaction: discord.Interaction):
    results = await asyncio.gather(*[_token_worker(t, cfg, i) for i, t in enumerate(cfg["tokens"])])
    await _send_result(interaction, results, cfg)

# ── Eco mode: one token at a time, switch on ban ──────────────────────────────

async def run_eco(cfg: dict, interaction: discord.Interaction):
    ignore = set(cfg.get("ignore_ids", []))
    delay  = cfg["dm_options"]["delay"]
    user_ids = [u for u in cfg.get("user_ids", []) if u not in ignore]
    tokens = cfg.get("tokens", [])
    total_sent, total_errors = 0, 0
    idx = 0  # current token index

    while user_ids and idx < len(tokens):
        token = tokens[idx]
        client = discord.Client()
        remaining = []

        @client.event
        async def on_ready():
            nonlocal total_sent, total_errors
            if cfg.get("status"):
                await client.change_presence(activity=discord.Game(name=cfg["status"]))
            for uid in user_ids:
                try:
                    await _send_dm(client, uid, cfg)
                    total_sent += 1
                    print(f"[Eco Token {idx+1}] ✅ → {uid}")
                except discord.Forbidden:
                    remaining.append(uid)
                    total_errors += 1
                    print(f"[Eco Token {idx+1}] ❌ Banni/Fermé → switch token")
                    await client.close(); return
                except Exception as e:
                    total_errors += 1
                    print(f"[Eco Token {idx+1}] ❌ {uid}: {e}")
                await asyncio.sleep(delay)
            await client.close()

        try:
            await client.start(token, bot=False)
        except Exception as e:
            print(f"[Eco Token {idx+1}] ❌ Invalide: {e}")
            idx += 1; continue

        if remaining:
            user_ids = remaining
            idx += 1
        else:
            break

    res = [{"sent": total_sent, "errors": total_errors}]
    await _send_result(interaction, res, cfg)

# ── Result embed ──────────────────────────────────────────────────────────────

async def _send_result(interaction: discord.Interaction, results: list, cfg: dict):
    sent   = sum(r["sent"]   for r in results)
    errors = sum(r["errors"] for r in results)
    embed  = discord.Embed(
        title="🚀 DMall Terminé",
        color=0x57F287 if errors == 0 else 0xED4245
    )
    embed.add_field(name="✅ DMs envoyés",      value=str(sent),              inline=True)
    embed.add_field(name="❌ Erreurs",          value=str(errors),            inline=True)
    embed.add_field(name="🤖 Tokens utilisés", value=str(len(cfg["tokens"])),inline=True)
    embed.set_footer(text="by Ohio")
    try:
        await interaction.followup.send(embed=embed)
    except:
        pass

import os
import motor.motor_asyncio
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = _client["multidmall"]
col = db["config"]
CONFIG_ID = "main"

DEFAULT = {
    "_id": CONFIG_ID,
    "tokens": [],
    "message": "",
    "embed": {
        "enabled": False, "title": "", "description": "",
        "color": 5814783, "footer": "", "image_url": "",
        "thumbnail_url": "", "button_label": "", "button_url": ""
    },
    "user_ids": [],
    "ignore_ids": [],
    "dm_options": {"delay": 1.5, "stop_on_error": False, "max_errors": 10},
    "status": "",
    "authorized_users": []
}

async def load() -> dict:
    doc = await col.find_one({"_id": CONFIG_ID})
    if not doc:
        await col.insert_one({**DEFAULT})
        return {**DEFAULT}
    return doc

async def save(data: dict):
    data["_id"] = CONFIG_ID
    await col.replace_one({"_id": CONFIG_ID}, data, upsert=True)

async def set_field(field: str, value):
    await col.update_one({"_id": CONFIG_ID}, {"$set": {field: value}}, upsert=True)

async def authorized(user_id: int) -> bool:
    cfg = await load()
    auth = cfg.get("authorized_users", [])
    return not auth or user_id in auth

async def make_embed():
    import discord
    cfg = await load()
    e = discord.Embed(
        title="⚙️  Configuration du MultiDmall",
        description="*Utilisez les boutons ci-dessous pour configurer votre Dmall.*",
        color=0x5865F2
    )
    nb_tok = len(cfg.get("tokens", []))
    msg    = cfg.get("message", "")
    emb    = cfg.get("embed", {})
    ids    = len(cfg.get("user_ids", []))
    ign    = len(cfg.get("ignore_ids", []))
    delay  = cfg.get("dm_options", {}).get("delay", 1.5)

    # Ligne 1 : Tokens | Message
    e.add_field(name="🤖 Tokens",
                value=f"`{nb_tok}` token(s)" if nb_tok else "*Aucun token*", inline=True)
    e.add_field(name="📩 Message",
                value=f"```{msg[:50]}{'...' if len(msg)>50 else ''}```" if msg else "*Aucun message*",
                inline=True)
    e.add_field(name="\u200b", value="\u200b", inline=True)

    # Ligne 2 : Embed | User IDs | Ignorer
    e.add_field(name="📝 Embed",
                value=f"`{emb.get('title','')[:40]}`" if emb.get("enabled") else "*Aucun embed*",
                inline=True)
    e.add_field(name="👤 User IDs",      value=f"**{ids}** ID",          inline=True)
    e.add_field(name="🚫 IDs Ignorés",   value=f"**{ign}** ID",          inline=True)

    # Ligne 3 : Options DM
    e.add_field(name="⚙️ Options de DM", value=f"Délai : **{delay}s**",  inline=True)
    e.add_field(name="\u200b", value="\u200b", inline=True)
    e.add_field(name="\u200b", value="\u200b", inline=True)
    e.set_footer(text="by Ohio")
    return e

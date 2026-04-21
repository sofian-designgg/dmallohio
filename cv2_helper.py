"""
Discord Components V2 Helper
Permet d'envoyer des messages avec boutons intégrés dans les sections (layout type embed).
"""
import aiohttp
import discord


# ── Builders ──────────────────────────────────────────────────────────────────

def text(content: str) -> dict:
    return {"type": 10, "content": content}


def separator(divider: bool = True, spacing: int = 1) -> dict:
    return {"type": 14, "divider": divider, "spacing": spacing}


def button(label: str, custom_id: str, style: int = 1, emoji: str | None = None) -> dict:
    b = {"type": 2, "label": label, "custom_id": custom_id, "style": style}
    if emoji:
        b["emoji"] = {"name": emoji}
    return b


def link_button(label: str, url: str, emoji: str | None = None) -> dict:
    b = {"type": 2, "label": label, "url": url, "style": 5}
    if emoji:
        b["emoji"] = {"name": emoji}
    return b


def section(text_content: str, accessory_button: dict) -> dict:
    return {
        "type": 9,
        "components": [{"type": 10, "content": text_content}],
        "accessory": accessory_button,
    }


def action_row(*buttons: dict) -> dict:
    return {"type": 1, "components": list(buttons)}


def container(*components: dict, accent_color: int = 0x5865F2) -> dict:
    return {
        "type": 17,
        "accent_color": accent_color,
        "components": list(components),
    }


# ── Send helpers ──────────────────────────────────────────────────────────────

async def respond_v2(interaction: discord.Interaction, *components: dict, ephemeral: bool = False):
    """Répondre à une interaction avec un message Components V2."""
    flags = 32768  # IS_COMPONENTS_V2
    if ephemeral:
        flags |= 64

    url = (
        f"https://discord.com/api/v10/interactions/"
        f"{interaction.id}/{interaction.token}/callback"
    )
    payload = {
        "type": 4,
        "data": {
            "flags": flags,
            "components": list(components),
        },
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status not in (200, 204):
                text_resp = await resp.text()
                raise RuntimeError(f"Components V2 error {resp.status}: {text_resp}")


async def edit_v2(interaction: discord.Interaction, *components: dict):
    """Éditer le message original avec un layout Components V2."""
    url = (
        f"https://discord.com/api/v10/webhooks/"
        f"{interaction.application_id}/{interaction.token}/messages/@original"
    )
    payload = {
        "flags": 32768,
        "components": list(components),
    }
    async with aiohttp.ClientSession() as session:
        async with session.patch(url, json=payload) as resp:
            if resp.status not in (200, 204):
                text_resp = await resp.text()
                raise RuntimeError(f"Components V2 edit error {resp.status}: {text_resp}")


async def followup_v2(interaction: discord.Interaction, *components: dict, ephemeral: bool = False):
    """Envoyer un followup avec Components V2."""
    flags = 32768
    if ephemeral:
        flags |= 64
    url = (
        f"https://discord.com/api/v10/webhooks/"
        f"{interaction.application_id}/{interaction.token}"
    )
    payload = {
        "flags": flags,
        "components": list(components),
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status not in (200, 204):
                text_resp = await resp.text()
                raise RuntimeError(f"Components V2 followup error {resp.status}: {text_resp}")

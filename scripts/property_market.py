
import os
import json
import random
from pathlib import Path
from datetime import datetime, timezone

import requests

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data" / "market_state.json"
IMAGE_FILE = ROOT / "assets" / "prime-city-district-map.png"

WEBHOOK = os.environ["PROPERTY_MARKET_DISCORD_WEBHOOK_URL"]

BASE_PRICES = {
    "District 1": 2_000_000,
    "District 2": 3_000_000,
    "District 3": 4_000_000,
    "District 4": 5_000_000,
    "District 5": 6_500_000,
    "District 6": 8_000_000,
}

MAX_CHANGE = 0.05
HOURLY_MOVEMENT = 0.015
STEP = 10_000
IMAGE_NAME = "prime-city-district-map.png"

def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())

    return {
        "message_id": None,
        "last_update_hour": None,
        "updated_at": None,
        "prices": BASE_PRICES.copy()
    }

def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2) + "\n"
    )

def round_price(value):
    return int(round(value / STEP) * STEP)

def update_prices(state, hour_key):
    if state.get("last_update_hour") == hour_key:
        return

    prices = state.get("prices", BASE_PRICES.copy())

    for district, base in BASE_PRICES.items():
        current = prices.get(district, base)

        movement = random.uniform(
            -HOURLY_MOVEMENT,
            HOURLY_MOVEMENT
        )

        updated = current * (1 + movement)

        updated = max(
            base * (1 - MAX_CHANGE),
            min(updated, base * (1 + MAX_CHANGE))
        )

        prices[district] = round_price(updated)

    state["prices"] = prices
    state["last_update_hour"] = hour_key
    state["updated_at"] = int(
        datetime.now(timezone.utc).timestamp()
    )

def create_embed(state):
    timestamp = state["updated_at"]

    price_lines = [
        f"**{district}** — `${price:,.0f}`"
        for district, price in state["prices"].items()
    ]

    return {
        "title": "👑 PRIME CITY",
        "description": (
            "## OFFICIAL PROPERTY MARKET\n"
            "🟢 **LIVE MARKET**\n\n"
            "### MARKET DATE & TIME\n"
            f"<t:{timestamp}:F>\n"
            "*Displayed in each viewer's local time.*\n\n"
            "### DISTRICT PURCHASE PRICES\n"
            + "\n".join(price_lines)
            + "\n\n━━━━━━━━━━━━━━━━━━━━\n"
            "🏠 **PROPERTY PRICING NOTICE**\n"
            "Final property prices are subject to interior choice. "
            "Different interior selections may affect the final "
            "purchase price.\n\n"
            "📊 Prices are subject to hourly market adjustments."
        ),
        "color": 0xEC329C,
        "image": {
            "url": f"attachment://{IMAGE_NAME}"
        },
        "footer": {
            "text": "PRIME CITY REAL ESTATE • OFFICIAL MARKET BULLETIN"
        }
    }

def send_or_edit(state):
    if not IMAGE_FILE.exists():
        raise FileNotFoundError(
            f"District map missing: {IMAGE_FILE}"
        )

    payload = {
        "username": "PRIME CITY | PROPERTY MARKET",
        "embeds": [create_embed(state)]
    }

    if state.get("message_id"):
        url = f"{WEBHOOK}/messages/{state['message_id']}"

        with IMAGE_FILE.open("rb") as image:
            response = requests.patch(
                url,
                data={"payload_json": json.dumps(payload)},
                files={
                    "files[0]": (
                        IMAGE_NAME,
                        image,
                        "image/png"
                    )
                },
                timeout=30
            )

        if response.status_code != 404:
            response.raise_for_status()
            return

        state["message_id"] = None

    with IMAGE_FILE.open("rb") as image:
        response = requests.post(
            WEBHOOK + "?wait=true",
            data={"payload_json": json.dumps(payload)},
            files={
                "files[0]": (
                    IMAGE_NAME,
                    image,
                    "image/png"
                )
            },
            timeout=30
        )

    response.raise_for_status()
    state["message_id"] = response.json()["id"]

def main():
    state = load_state()

    now = datetime.now(timezone.utc)
    hour_key = now.strftime("%Y-%m-%d-%H")

    update_prices(state, hour_key)
    send_or_edit(state)
    save_state(state)

    print("PRIME CITY MARKET UPDATED")
    print(state["prices"])

if __name__ == "__main__":
    main()

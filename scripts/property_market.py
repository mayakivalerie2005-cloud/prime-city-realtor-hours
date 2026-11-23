
import os
import json
import random
from pathlib import Path
from datetime import datetime, timezone

import requests

# ==========================================
# PRIME CITY - LIVE PROPERTY MARKET
# ==========================================

ROOT = Path(__file__).resolve().parents[1]

STATE_FILE = ROOT / "data" / "market_state.json"
IMAGE_FILE = ROOT / "assets" / "prime-city-district-map.png"

WEBHOOK = os.environ["PROPERTY_MARKET_DISCORD_WEBHOOK_URL"]

IMAGE_NAME = "prime-city-district-map.png"

BASE_PRICES = {
    "District 1": 2_000_000,
    "District 2": 3_000_000,
    "District 3": 4_000_000,
    "District 4": 5_000_000,
    "District 5": 6_500_000,
    "District 6": 8_000_000,
}

HOURLY_MOVEMENT = 0.015
MAX_CHANGE = 0.05
STEP = 10_000

# ==========================================
# LOAD AND SAVE MARKET DATA
# ==========================================

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

# ==========================================
# PRICE CALCULATIONS
# ==========================================

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

        lower_limit = base * (1 - MAX_CHANGE)
        upper_limit = base * (1 + MAX_CHANGE)

        updated = max(
            lower_limit,
            min(updated, upper_limit)
        )

        prices[district] = round_price(updated)

    state["prices"] = prices
    state["last_update_hour"] = hour_key
    state["updated_at"] = int(
        datetime.now(timezone.utc).timestamp()
    )

# ==========================================
# DISCORD MARKET MESSAGE
# ==========================================

def create_embed(state):

    timestamp = state["updated_at"]

    price_lines = [
        f"**{district}** — `${price:,.0f}`"
        for district, price in state["prices"].items()
    ]

    description = (
        "## OFFICIAL PROPERTY MARKET\n"
        "🟢 **LIVE MARKET**\n"
        "### MARKET DATE & TIME\n"
        f"<t:{timestamp}:F>\n"
        "*Displayed in each viewer's local time.*\n"
        "### DISTRICT PURCHASE PRICES\n"
        + "\n".join(price_lines)
        + "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🏠 **PROPERTY PRICING NOTICE**\n"
        "Final property prices are subject to interior choice. "
        "Different interior selections may affect the final purchase price.\n"
        "📊 Prices are subject to hourly market adjustments."
    )

    return {
        "title": "👑 PRIME CITY",
        "description": description,
        "color": 0xEC329C,
        "image": {
            "url": f"attachment://{IMAGE_NAME}"
        },
        "footer": {
            "text": "PRIME CITY REAL ESTATE • OFFICIAL MARKET BULLETIN"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ==========================================
# SEND OR UPDATE DISCORD MESSAGE
# ==========================================

def send_or_edit(state):

    if not IMAGE_FILE.exists():
        raise FileNotFoundError(
            f"District map not found: {IMAGE_FILE}"
        )

    payload = {
        "username": "PRIME CITY | PROPERTY MARKET",
        "embeds": [create_embed(state)],
        "attachments": [
            {
                "id": 0,
                "filename": IMAGE_NAME
            }
        ]
    }

    if state.get("message_id"):

        url = (
            f"{WEBHOOK}/messages/"
            f"{state['message_id']}"
        )

        with IMAGE_FILE.open("rb") as image:

            response = requests.patch(
                url,
                data={
                    "payload_json": json.dumps(payload)
                },
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

    # Create the original market post

    with IMAGE_FILE.open("rb") as image:

        response = requests.post(
            WEBHOOK + "?wait=true",
            data={
                "payload_json": json.dumps(payload)
            },
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

# ==========================================
# MAIN AUTOMATION
# ==========================================

def main():

    state = load_state()

    now = datetime.now(timezone.utc)

    hour_key = now.strftime("%Y-%m-%d-%H")

    update_prices(state, hour_key)

    send_or_edit(state)

    save_state(state)

    print("================================")
    print("PRIME CITY PROPERTY MARKET")
    print("MARKET UPDATE SUCCESSFUL")
    print("================================")

    for district, price in state["prices"].items():
        print(f"{district}: ${price:,.0f}")

    print("Discord Message ID:", state["message_id"])

if __name__ == "__main__":
    main()

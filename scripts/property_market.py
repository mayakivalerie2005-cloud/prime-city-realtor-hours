
import os
import json
import random
from pathlib import Path
from datetime import datetime, timezone

import requests

# ==========================================
# PRIME CITY - WEEKLY PROPERTY MARKET
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

MAX_INCREASE = 1_000_000
MAX_WEEKLY_MOVEMENT = 200_000
STEP = 10_000

# Weekly probability:
# 42.5% increase, 42.5% decrease, 15% unchanged.

# ==========================================
# MARKET STATE
# ==========================================

def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    else:
        state = {}

    state.setdefault("message_id", None)
    state.setdefault("last_update_week", None)
    state.setdefault("updated_at", None)
    state.setdefault("prices", BASE_PRICES.copy())
    state.setdefault("previous_prices", BASE_PRICES.copy())
    state.setdefault("changes", {})

    return state

def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2) + "\n"
    )

# ==========================================
# RANDOM WEEKLY PRICE MOVEMENT
# ==========================================

def round_price(value):
    return int(round(value / STEP) * STEP)

def update_prices(state, week_key):

    # Prevent multiple changes during the same week.
    if state.get("last_update_week") == week_key:
        return

    current_prices = state["prices"].copy()
    previous_prices = current_prices.copy()
    new_prices = {}
    changes = {}

    for district, base in BASE_PRICES.items():

        old_price = current_prices.get(district, base)

        # Random market direction.
        direction = random.choices(
            ["up", "down", "same"],
            weights=[42.5, 42.5, 15],
            k=1
        )[0]

        if direction == "same":
            new_price = old_price

        else:
            amount = random.randrange(
                STEP,
                MAX_WEEKLY_MOVEMENT + STEP,
                STEP
            )

            if direction == "up":
                new_price = old_price + amount
            else:
                new_price = old_price - amount

        # Permanent minimum and maximum limits.
        minimum = base
        maximum = base + MAX_INCREASE

        new_price = max(
            minimum,
            min(new_price, maximum)
        )

        new_price = round_price(new_price)

        # Save movement.
        difference = new_price - old_price

        new_prices[district] = new_price

        changes[district] = {
            "previous": old_price,
            "current": new_price,
            "difference": difference
        }

    state["previous_prices"] = previous_prices
    state["prices"] = new_prices
    state["changes"] = changes
    state["last_update_week"] = week_key
    state["updated_at"] = int(
        datetime.now(timezone.utc).timestamp()
    )

# ==========================================
# PRICE DISPLAY
# ==========================================

def format_price(value):
    return f"${value:,.0f}"

def format_change(difference):

    if difference > 0:
        return f"🟢 ↑ +{format_price(difference)}"

    if difference < 0:
        return f"🔴 ↓ -{format_price(abs(difference))}"

    return "⚪ → NO CHANGE"

def create_price_report(state):

    lines = []

    for district in BASE_PRICES:

        movement = state["changes"].get(district, {})

        previous = movement.get(
            "previous",
            state["prices"][district]
        )

        current = state["prices"][district]

        difference = current - previous

        lines.append(
            f"**{district}**\n"
            f"`{format_price(previous)}` → "
            f"`{format_price(current)}`\n"
            f"{format_change(difference)}"
        )

    return "\n".join(lines)

# ==========================================
# DISCORD EMBED
# ==========================================

def create_embed(state):

    timestamp = state["updated_at"]

    description = (
        "## OFFICIAL PROPERTY MARKET\n"
        "🟢 **WEEKLY MARKET REPORT**\n"
        "### MARKET DATE & TIME\n"
        f"<t:{timestamp}:F>\n"
        "*Displayed in each viewer's local time.*\n"
        "### DISTRICT PURCHASE PRICES\n"
        f"{create_price_report(state)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🏠 **PROPERTY PRICING NOTICE**\n"
        "Final property prices are subject to interior choice. "
        "Different interior selections may affect the final purchase price.\n"
        "📊 Prices fluctuate weekly according to market conditions."
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
# DISCORD WEBHOOK
# ==========================================

def send_or_edit(state):

    if not IMAGE_FILE.exists():
        raise FileNotFoundError(
            f"District map missing: {IMAGE_FILE}"
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

    message_id = state.get("message_id")

    if message_id:

        url = f"{WEBHOOK}/messages/{message_id}"

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

    # Create a new post if no existing message is available.
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
# MAIN
# ==========================================

def main():

    state = load_state()

    now = datetime.now(timezone.utc)

    week_key = now.strftime("%G-W%V")

    update_prices(state, week_key)

    send_or_edit(state)

    save_state(state)

    print("================================")
    print("PRIME CITY WEEKLY MARKET")
    print("MARKET UPDATE SUCCESSFUL")
    print("================================")

    for district, price in state["prices"].items():
        print(f"{district}: {format_price(price)}")

    print("Message ID:", state["message_id"])

if __name__ == "__main__":
    main()

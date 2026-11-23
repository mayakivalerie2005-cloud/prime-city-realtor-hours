
import os
import json
import random
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests

# ==========================================
# PRIME CITY - WEEKLY PROPERTY MARKET
# ==========================================

ROOT = Path(__file__).resolve().parents[1]

STATE_FILE = ROOT / "data" / "market_state.json"
IMAGE_FILE = ROOT / "assets" / "prime-city-district-map.png"

WEBHOOK = os.environ["PROPERTY_MARKET_DISCORD_WEBHOOK_URL"]

IMAGE_NAME = "prime-city-district-map.png"

# ==========================================
# OFFICIAL BASE PRICES
# ==========================================

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

# Weekly movement probabilities:
# 42.5% increase
# 42.5% decrease
# 15% unchanged

# Official update: Every Monday at 08:00 UTC.

# ==========================================
# STATE MANAGEMENT
# ==========================================

def load_state():

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if STATE_FILE.exists():
        with STATE_FILE.open("r", encoding="utf-8") as file:
            state = json.load(file)
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

    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)
        file.write("\n")

# ==========================================
# PRICE PROTECTION
# ==========================================

def round_price(value):
    return int(round(value / STEP) * STEP)

def protect_price(district, value):

    base = BASE_PRICES[district]
    maximum = base + MAX_INCREASE

    value = round_price(value)

    return max(base, min(value, maximum))

def repair_prices(prices):

    repaired = {}

    for district, base in BASE_PRICES.items():
        saved = prices.get(district, base)
        repaired[district] = protect_price(district, saved)

    return repaired

# ==========================================
# MARKET WEEK CALCULATION
# ==========================================

def get_market_week_key(now):

    monday = now - timedelta(days=now.weekday())

    week_start = monday.replace(
        hour=8,
        minute=0,
        second=0,
        microsecond=0
    )

    if now < week_start:
        week_start -= timedelta(days=7)

    return week_start.strftime("%Y-%m-%dT%H:%M:%S")

# ==========================================
# NEXT MARKET UPDATE
# ==========================================

def get_next_update(now):

    days_until_monday = (7 - now.weekday()) % 7

    next_update = now.replace(
        hour=8,
        minute=0,
        second=0,
        microsecond=0
    ) + timedelta(days=days_until_monday)

    if next_update <= now:
        next_update += timedelta(days=7)

    return int(next_update.timestamp())

# ==========================================
# PRICE FORMATTING
# ==========================================

def format_price(value):
    return f"${value:,.0f}"

def format_change(difference):

    if difference > 0:
        return f"🟢 ↑ +{format_price(difference)}"

    if difference < 0:
        return f"🔴 ↓ -{format_price(abs(difference))}"

    return "⚪ → NO CHANGE"

# ==========================================
# RANDOM WEEKLY PRICE MOVEMENTS
# ==========================================

def update_prices(state, week_key, now):

    current_prices = repair_prices(
        state.get("prices", {})
    )

    previous_prices = repair_prices(
        state.get("previous_prices", current_prices)
    )

    state["prices"] = current_prices
    state["previous_prices"] = previous_prices

    # Prevent multiple price changes in one market week.
    if state.get("last_update_week") == week_key:

        state["changes"] = {
            district: {
                "previous": previous_prices[district],
                "current": current_prices[district],
                "difference": (
                    current_prices[district]
                    - previous_prices[district]
                )
            }
            for district in BASE_PRICES
        }

        if not state.get("updated_at"):
            state["updated_at"] = int(now.timestamp())

        return

    previous_prices = current_prices.copy()

    new_prices = {}
    changes = {}

    for district in BASE_PRICES:

        old_price = current_prices[district]

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

        new_price = protect_price(district, new_price)

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
    state["updated_at"] = int(now.timestamp())

# ==========================================
# WEEKLY MARKET REPORT
# ==========================================

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
            f"**{district}** — "
            f"`{format_price(previous)}` → "
            f"`{format_price(current)}` "
            f"{format_change(difference)}"
        )

    return "\n".join(lines)

# ==========================================
# DISCORD EMBED - COMPACT DESIGN
# ==========================================

def create_embed(state, next_update):

    timestamp = state["updated_at"]

    description = (
        "## OFFICIAL PROPERTY MARKET\n"
        "🟢 **WEEKLY MARKET REPORT**\n"
        f"🕒 Updated: <t:{timestamp}:F>\n"
        "*Times shown in your local timezone.*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "### DISTRICT PURCHASE PRICES\n"
        f"{create_price_report(state)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⏰ **NEXT MARKET UPDATE**\n"
        f"📅 <t:{next_update}:F>\n"
        f"🕒 <t:{next_update}:R>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🏠 **PROPERTY PRICING NOTICE**\n"
        "Final property prices are subject to interior choice. "
        "Different interior selections may affect the final purchase price."
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

def send_or_edit(state, next_update):

    if not IMAGE_FILE.exists():
        raise FileNotFoundError(
            f"District map missing: {IMAGE_FILE}"
        )

    payload = {
        "username": "PRIME CITY | PROPERTY MARKET",
        "embeds": [
            create_embed(state, next_update)
        ],
        "attachments": [
            {
                "id": 0,
                "filename": IMAGE_NAME
            }
        ]
    }

    message_id = state.get("message_id")

    # Edit existing Discord announcement.
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

        # Recreate if the old message no longer exists.
        state["message_id"] = None

    # Create a new announcement if necessary.
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

    week_key = get_market_week_key(now)

    next_update = get_next_update(now)

    update_prices(state, week_key, now)

    send_or_edit(state, next_update)

    save_state(state)

    print("======================================")
    print("       PRIME CITY PROPERTY MARKET")
    print("======================================")

    for district, base in BASE_PRICES.items():

        price = state["prices"][district]

        assert base <= price <= base + MAX_INCREASE

        print(f"{district}: {format_price(price)}")

    print("--------------------------------------")
    print("ALL PRICE LIMITS VERIFIED")
    print("WEEKLY MARKET UPDATE SUCCESSFUL")
    print("NEXT UPDATE:", next_update)
    print("MESSAGE ID:", state["message_id"])
    print("======================================")

if __name__ == "__main__":
    main()

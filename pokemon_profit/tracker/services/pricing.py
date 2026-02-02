import time
import requests
import certifi
from django.conf import settings

BASE_URL = "https://api.pokemontcg.io/v2/cards"

def fetch_card_price(card_name: str, set_name: str = "", card_number: str = ""):
    headers = {}
    if getattr(settings, "POKEMONTCG_API_KEY", None):
        headers["X-Api-Key"] = settings.POKEMONTCG_API_KEY

    parts = [f'name:"{card_name}"']
    if set_name:
        parts.append(f'set.name:"{set_name}"')
    if card_number:
        num = card_number.split("/")[0].strip()
        if num:
            parts.append(f'number:"{num}"')
    q = " ".join(parts)

    params = {"q": q, "pageSize": 1}

    # Retry settings
    attempts = 3
    timeout_seconds = 45

    last_exc = None
    for i in range(attempts):
        try:
            resp = requests.get(
                BASE_URL,
                headers=headers,
                params=params,
                timeout=timeout_seconds,
                verify=certifi.where(),
            )
            resp.raise_for_status()
            data = resp.json()

            cards = data.get("data", [])
            if not cards:
                return None

            card = cards[0]
            tcgplayer = card.get("tcgplayer") or {}
            prices = tcgplayer.get("prices") or {}

            for variant in ["holofoil", "normal", "reverseHolofoil", "1stEditionHolofoil", "1stEditionNormal"]:
                p = prices.get(variant)
                if isinstance(p, dict):
                    return p.get("market") or p.get("mid") or p.get("low")

            return None

        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            last_exc = e
            # exponential-ish backoff: 2s, 4s, 6s
            time.sleep(2 * (i + 1))
            continue

    return None

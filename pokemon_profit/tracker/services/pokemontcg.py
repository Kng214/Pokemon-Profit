import requests
import certifi
from django.conf import settings

BASE = "https://api.pokemontcg.io/v2"

def _headers():
    h = {}
    key = getattr(settings, "POKEMONTCG_API_KEY", None)
    if key:
        h["X-Api-Key"] = key
    return h

def fetch_card_by_set_and_number(set_name: str, number: str, page_size: int = 25):
    """
    Finds the *exact* card from pokemontcg.io using set name + number.
    Returns the best matching card dict or None.
    """
    set_name = (set_name or "").strip()
    number = (number or "").strip()

    q = f'set.name:"{set_name}" number:"{number}"'

    r = requests.get(
        f"{BASE}/cards",
        headers=_headers(),
        params={"q": q, "pageSize": page_size},
        timeout=30,
        verify=certifi.where(),
    )
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        return None

    return data[0]

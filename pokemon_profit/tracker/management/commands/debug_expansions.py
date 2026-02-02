from django.core.management.base import BaseCommand
import requests, certifi
from django.conf import settings

BASE = "https://api.tcgapis.com/api/v1"

class Command(BaseCommand):
    help = "Debug expansions endpoint responses."

    def add_arguments(self, parser):
        parser.add_argument("--start", type=int, default=1)
        parser.add_argument("--end", type=int, default=30)

    def handle(self, *args, **opts):
        h = {"x-api-key": settings.TCGAPIS_API_KEY}

        for cid in range(opts["start"], opts["end"] + 1):
            url = f"{BASE}/expansions/{cid}"
            try:
                r = requests.get(url, headers=h, timeout=10, verify=certifi.where())
                self.stdout.write(f"{cid}: {r.status_code} {url}")
                self.stdout.write(r.text[:300])
                self.stdout.write("-" * 60)
            except Exception as e:
                self.stdout.write(f"{cid}: ERROR {e}")
                self.stdout.write("-" * 60)

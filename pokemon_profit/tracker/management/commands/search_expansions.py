from django.core.management.base import BaseCommand
from tracker.services.tcgapis import get_expansions

POKEMON_CATEGORY_ID = 3

class Command(BaseCommand):
    help = "Search Pokemon expansions by keyword"

    def add_arguments(self, parser):
        parser.add_argument("keyword", type=str)

    def handle(self, *args, **options):
        kw = options["keyword"].lower().strip()

        data = get_expansions(POKEMON_CATEGORY_ID)
        expansions = data.get("data", {}).get("expansions", [])

        matches = []
        for e in expansions:
            name = (e.get("name") or "")
            if kw in name.lower():
                matches.append(e)

        self.stdout.write(f"Matches for '{kw}': {len(matches)}")
        for e in matches[:100]:
            self.stdout.write(f"- {e.get('name')} (groupId={e.get('groupId')})")

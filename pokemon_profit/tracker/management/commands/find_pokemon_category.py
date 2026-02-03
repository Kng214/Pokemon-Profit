from django.core.management.base import BaseCommand
from tracker.services.tcgapis import get_expansions

class Command(BaseCommand):
    help = "Find the TCGAPIs categoryId that returns Pokémon expansions."

    def add_arguments(self, parser):
        parser.add_argument("--start", type=int, default=1)
        parser.add_argument("--end", type=int, default=200)

    def handle(self, *args, **options):
        start = options["start"]
        end = options["end"]

        self.stdout.write(f"Searching categoryId {start}..{end} for Pokémon expansions...")

        for cid in range(start, end + 1):
            try:
                data = get_expansions(cid)
                expansions = None
                if isinstance(data, dict):
                    expansions = data.get("expansions") or data.get("results") or data.get("data")

                if expansions and isinstance(expansions, list) and len(expansions) > 0:
                    sample = expansions[0]
                    self.stdout.write(self.style.SUCCESS(
                        f"Found categoryId={cid} with {len(expansions)} expansions. Sample: {str(sample)[:200]}"
                    ))
                    self.stdout.write(self.style.SUCCESS(
                        f"Use this categoryId for Pokémon: {cid}"
                    ))
                    return

            except Exception:
                continue

        self.stdout.write(self.style.ERROR("No categoryId found in that range. Try a larger range."))

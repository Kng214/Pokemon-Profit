import json
import zipfile
import os
from django.core.management.base import BaseCommand
from tracker.models import CardCatalog

class Command(BaseCommand):
    help = "Import Pokemon card catalog from PokemonTCG/pokemon-tcg-data ZIP."

    def add_arguments(self, parser):
        parser.add_argument("zip_path", type=str, help="Path to pokemon-tcg-data ZIP")
        parser.add_argument("--language", type=str, default="en")
        parser.add_argument("--limit", type=int, default=0)

    def _load_sets_map(self, z: zipfile.ZipFile, lang: str) -> dict:
        """
        Returns { set_id: set_name } from ZIP.
        Common path: */sets/en.json
        """
        candidates = [n for n in z.namelist() if n.endswith(f"sets/{lang}.json")]
        if not candidates:
            # fallback: print hint by returning empty map
            return {}

        raw = z.read(candidates[0]).decode("utf-8")
        sets = json.loads(raw)
        if isinstance(sets, dict) and "data" in sets:
            sets = sets["data"]
        if not isinstance(sets, list):
            return {}

        return {str(s.get("id")): str(s.get("name")) for s in sets if s.get("id") and s.get("name")}

    def handle(self, *args, **opts):
        zip_path = opts["zip_path"]
        lang = opts["language"]
        limit = opts["limit"]

        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"ZIP not found: {zip_path}")

        # wipe existing
        CardCatalog.objects.all().delete()

        created = 0
        updated = 0
        total_processed = 0
        total_saved = 0

        with zipfile.ZipFile(zip_path, "r") as z:
            sets_map = self._load_sets_map(z, lang)
            self.stdout.write(f"Loaded {len(sets_map)} sets from ZIP for lang='{lang}'")

            if not sets_map:
                self.stdout.write(self.style.WARNING(
                    "Could not find sets/<lang>.json in ZIP. Set names will be blank unless derived."
                ))

            # Expect: */cards/en/<set_id>.json
            card_files = [
                n for n in z.namelist()
                if f"/cards/{lang}/" in n and n.endswith(".json")
            ]
            self.stdout.write(f"Found {len(card_files)} card JSON files in ZIP for lang='{lang}'")
            if not card_files:
                sample = z.namelist()[:40]
                self.stdout.write(self.style.ERROR("No card files matched. ZIP sample paths:"))
                for s in sample:
                    self.stdout.write("  " + s)
                return

            for f in card_files:
                # set_id is the filename without extension (e.g. base1.json -> base1)
                filename = f.split("/")[-1]
                set_id = filename.replace(".json", "").strip()
                set_name = sets_map.get(set_id, "")  # may be blank if sets_map missing

                raw = z.read(f).decode("utf-8")
                cards = json.loads(raw)

                if isinstance(cards, dict) and "data" in cards:
                    cards = cards["data"]
                if not isinstance(cards, list):
                    continue

                for c in cards:
                    total_processed += 1

                    cid = str(c.get("id") or "").strip()
                    name = (c.get("name") or "").strip()
                    number = str(c.get("number") or "").strip()

                    images = c.get("images") or {}
                    image_small = images.get("small")
                    image_large = images.get("large")

                    rarity = c.get("rarity")

                    # Now set_id/set_name are derived from filename + sets_map
                    if not (cid and name and set_id and number):
                        continue

                    _, was_created = CardCatalog.objects.update_or_create(
                        catalog_id=cid,
                        defaults=dict(
                            name=name[:255],
                            set_id=set_id[:80],
                            set_name=(set_name[:255] if set_name else ""),
                            number=number[:20],
                            rarity=(rarity[:100] if isinstance(rarity, str) else None),
                            image_small=image_small,
                            image_large=image_large,
                        ),
                    )

                    created += int(was_created)
                    updated += int(not was_created)
                    total_saved += 1

                    if limit and total_saved >= limit:
                        self.stdout.write(self.style.SUCCESS(
                            f"Stopped early at limit={limit}. saved={total_saved}"
                        ))
                        self.stdout.write(self.style.SUCCESS(
                            f"DB count now: {CardCatalog.objects.count()}"
                        ))
                        return

        self.stdout.write(self.style.SUCCESS(
            f"Import done. saved={total_saved}, created={created}, updated={updated}, processed={total_processed}"
        ))
        self.stdout.write(self.style.SUCCESS(f"DB count now: {CardCatalog.objects.count()}"))

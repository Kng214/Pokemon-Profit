import re
from django.core.management.base import BaseCommand
from tracker.models import Card, SealedProduct, CatalogItem

def norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tokens(s: str) -> set[str]:
    t = set(norm(s).split())
    # remove very common junk words
    stop = {"the", "and", "of", "a", "an", "tcg", "pokemon", "pokémon", "sv", "scarlet", "violet"}
    return {w.rstrip("s") for w in t if w not in stop and len(w) > 1}

def base_number(n: str) -> str:
    return (n or "").split("/")[0].strip()

class Command(BaseCommand):
    help = "Auto-link owned Cards and SealedProducts to CatalogItem using imported TCGCSV catalog."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--cards-only", action="store_true")
        parser.add_argument("--sealed-only", action="store_true")

    def handle(self, *args, **opts):
        force = opts["force"]
        cards_only = opts["cards_only"]
        sealed_only = opts["sealed_only"]

        linked_cards = linked_sealed = 0
        skipped_cards = skipped_sealed = 0

        # ---------------- CARDS ----------------
        if not sealed_only:
            for c in Card.objects.all():
                if c.catalog_item_id and not force:
                    skipped_cards += 1
                    continue

                num = base_number(c.card_number)
                if not num:
                    self.stdout.write(self.style.WARNING(f"[CARD] Missing number: {c.name}"))
                    skipped_cards += 1
                    continue

                name_n = norm(c.name)
                printing = (c.printing or "").strip().lower()

                qs = CatalogItem.objects.filter(is_sealed=False)

                # First: narrow by number presence
                candidates = list(qs.filter(card_number__icontains=num)[:500])

                if not candidates:
                    self.stdout.write(self.style.WARNING(
                        f"[CARD] No catalog candidates for number {num}: {c.name}"
                    ))
                    skipped_cards += 1
                    continue

                best = None
                best_score = -1

                for item in candidates:
                    score = 0
                    item_name = norm(item.name)
                    item_num = (item.card_number or "")
                    item_print = (item.printing or "").strip().lower()

                    # number match
                    if num and num in item_num:
                        score += 20

                    # name match
                    if item_name == name_n:
                        score += 15
                    elif name_n and name_n in item_name:
                        score += 8

                    # printing match (bonus only)
                    if printing and item_print == printing:
                        score += 6

                    # set hint (bonus)
                    if hasattr(item, "set_name") and c.set_name and item.set_name:
                        if norm(c.set_name) in norm(item.set_name):
                            score += 4

                    if score > best_score:
                        best_score = score
                        best = item

                # Lower threshold since number is already strong
                if best and best_score >= 25:
                    c.catalog_item = best
                    c.save(update_fields=["catalog_item"])
                    linked_cards += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"[CARD] Linked {c.name} #{c.card_number} ({c.printing}) -> productId={best.product_id} "
                        f"catalog='{best.name}' [{best.printing}] score={best_score}"
                    ))
                else:
                    skipped_cards += 1
                    self.stdout.write(self.style.WARNING(
                        f"[CARD] Could not confidently link {c.name} #{c.card_number} ({c.printing}). best_score={best_score}"
                    ))

        # ---------------- SEALED ----------------
        if not cards_only:
            for s in SealedProduct.objects.all():
                if s.catalog_item_id and not force:
                    skipped_sealed += 1
                    continue

                owned_tokens = tokens(s.name)
                if not owned_tokens:
                    skipped_sealed += 1
                    continue

                qs = CatalogItem.objects.filter(is_sealed=True)

                best = None
                best_score = -1

                # Only scan first N for speed; should be fine if you're importing a single set CSV
                for item in qs[:2000]:
                    item_tokens = tokens(item.name)
                    overlap = len(owned_tokens & item_tokens)
                    if overlap == 0:
                        continue

                    score = overlap * 10

                    # bonus for set hint
                    if hasattr(item, "set_name") and s.set_name and item.set_name:
                        if norm(s.set_name) in norm(item.set_name):
                            score += 6

                    if score > best_score:
                        best_score = score
                        best = item

                if best and best_score >= 10:
                    s.catalog_item = best
                    s.save(update_fields=["catalog_item"])
                    linked_sealed += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"[SEALED] Linked '{s.name}' -> productId={best.product_id} catalog='{best.name}' score={best_score}"
                    ))
                else:
                    skipped_sealed += 1
                    self.stdout.write(self.style.WARNING(
                        f"[SEALED] Could not confidently link '{s.name}'. Try making the name closer to catalog."
                    ))

        self.stdout.write(self.style.SUCCESS(
            f"Done ✅ cards_linked={linked_cards}, cards_skipped={skipped_cards}, "
            f"sealed_linked={linked_sealed}, sealed_skipped={skipped_sealed}"
        ))

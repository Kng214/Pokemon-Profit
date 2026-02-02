from difflib import SequenceMatcher
from django.core.management.base import BaseCommand
from tracker.models import Card
from tracker.services.tcgapis import get_expansions, get_cards_by_group

POKEMON_CATEGORY_ID = 3

def norm(s: str) -> str:
    return (s or "").strip().lower()

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def best_expansion_match(card_set_name: str, expansions: list[dict]):
    """
    Returns (group_id, expansion_name, score) or (None, None, 0.0)
    """
    target = norm(card_set_name)
    if not target:
        return None, None, 0.0

    best = (None, None, 0.0)

    for e in expansions:
        e_name = e.get("name") or ""
        e_norm = norm(e_name)
        gid = e.get("groupId")

        if not gid or not e_norm:
            continue

        # quick contains boost
        if target in e_norm or e_norm in target:
            return gid, e_name, 1.0

        score = similarity(target, e_norm)
        if score > best[2]:
            best = (gid, e_name, score)

    return best

def best_card_match(card_name: str, card_number: str, group_cards: list[dict]):
    """
    Returns matched card dict or None.
    Uses (name + number) exact-ish first, then fuzzy name fallback.
    """
    target_name = norm(card_name)
    target_num = (card_number or "").split("/")[0].strip()

    # 1) Strong match: name + number
    if target_num:
        for c in group_cards:
            c_name = norm(c.get("name"))
            c_num = str(c.get("number") or "").strip()
            if c_name == target_name and c_num == target_num:
                return c

        # 2) Number-only match (if names differ slightly like punctuation)
        for c in group_cards:
            c_num = str(c.get("number") or "").strip()
            if c_num == target_num:
                return c

    # 3) Name contains / exact normalized
    for c in group_cards:
        c_name = norm(c.get("name"))
        if c_name == target_name:
            return c
        if target_name and (target_name in c_name or c_name in target_name):
            return c

    # 4) Fuzzy name match
    best = (None, 0.0)
    for c in group_cards:
        c_name_raw = c.get("name") or ""
        c_name = norm(c_name_raw)
        if not c_name:
            continue
        score = similarity(target_name, c_name)
        if score > best[1]:
            best = (c, score)

    # Require a decent similarity so we don't link wrong cards
    if best[0] is not None and best[1] >= 0.78:
        return best[0]

    return None

class Command(BaseCommand):
    help = "Link Cards to TCGAPIs group_id + product_id using fuzzy set matching + card matching."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-set-score",
            type=float,
            default=0.70,
            help="Minimum similarity score for set name matching (0-1).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-link even if tcgapis_product_id already exists.",
        )

    def handle(self, *args, **options):
        min_set_score = options["min_set_score"]
        force = options["force"]

        exp_json = get_expansions(POKEMON_CATEGORY_ID)
        expansions = exp_json.get("data", {}).get("expansions", [])

        if not expansions:
            self.stdout.write(self.style.ERROR("No expansions returned from TCGAPIs for Pokemon (categoryId=3)."))
            return

        linked = 0
        skipped = 0

        for card in Card.objects.all():
            if card.tcgapis_product_id and not force:
                self.stdout.write(f"Already linked: {card.name} (productId={card.tcgapis_product_id})")
                continue

            group_id, exp_name, score = best_expansion_match(card.set_name, expansions)

            if not group_id or score < min_set_score:
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"Set not found for '{card.set_name}' (best='{exp_name}' score={score:.2f}) | Card: {card.name}"
                ))
                continue

            # Save group id
            if card.tcgapis_group_id != group_id:
                card.tcgapis_group_id = group_id
                card.save(update_fields=["tcgapis_group_id"])

            # Pull all cards in the expansion group
            cards_json = get_cards_by_group(group_id)
            group_cards = cards_json.get("data", {}).get("cards", [])

            if not group_cards:
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"No cards returned for groupId={group_id} ({exp_name})"
                ))
                continue

            match = best_card_match(card.name, card.card_number, group_cards)

            if not match:
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"No card match in '{exp_name}' for '{card.name}' #{card.card_number}"
                ))
                # Helpful: print a few nearby-looking names
                sample = [c.get("name") for c in group_cards[:10]]
                self.stdout.write(f"Sample cards in set: {sample}")
                continue

            product_id = match.get("productId") or match.get("productID") or match.get("id")
            if not product_id:
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"Matched card but no productId field for '{card.name}' in '{exp_name}'"
                ))
                continue

            card.tcgapis_product_id = int(product_id)
            card.save(update_fields=["tcgapis_product_id"])

            linked += 1
            self.stdout.write(self.style.SUCCESS(
                f"Linked {card.name} [{card.card_number}] | set='{exp_name}' (score={score:.2f}) "
                f"-> groupId={group_id}, productId={card.tcgapis_product_id}"
            ))

        self.stdout.write(f"Done. Linked={linked}, Skipped={skipped}")

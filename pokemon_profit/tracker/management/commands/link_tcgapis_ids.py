import re
from django.core.management.base import BaseCommand
from tracker.models import Card
from tracker.services.tcgapis import get_all_expansions, get_cards_by_group

POKEMON_CATEGORY_ID = 3

def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def digits(s: str) -> set[str]:
    return set(re.findall(r"\d+", s or ""))

class Command(BaseCommand):
    help = "Link cards to TCGAPIs by scanning ALL expansions pages + card search."

    def add_arguments(self, parser):
        parser.add_argument("--max-exp-pages", type=int, default=30)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        max_pages = options["max_exp_pages"]
        force = options["force"]

        expansions = get_all_expansions(POKEMON_CATEGORY_ID, max_pages=max_pages)
        self.stdout.write(f"Loaded {len(expansions)} Pokemon expansions (pages up to {max_pages}).")

        if not expansions:
            self.stdout.write(self.style.ERROR("No expansions returned. Check API key / endpoint."))
            return

        linked = 0
        skipped = 0

        for card in Card.objects.all():
            if card.tcgapis_product_id and not force:
                self.stdout.write(f"Already linked: {card.name} (productId={card.tcgapis_product_id})")
                continue

            set_norm = norm(card.set_name)
            set_digits = digits(card.set_name)
            target_num = (card.card_number or "").split("/")[0].strip()
            name_norm = norm(card.name)
        
            candidates = expansions
            if set_digits:
                candidates = [e for e in expansions if (set_digits & digits(e.get("name", "")))]

            if not candidates or len(candidates) == 0:
                words = set(set_norm.split())
                candidates = [
                    e for e in expansions
                    if words and words.intersection(set(norm(e.get("name",""))).split())
                ]

            if not candidates:
                candidates = expansions

            best = None  

            for e in candidates[:60]: 
                gid = e.get("groupId")
                exp_name = e.get("name","")
                if not gid:
                    continue

                try:
                    max_card_pages = 12 if target_num else 2  

                    for page in range(1, max_card_pages + 1):
                        cards_json = get_cards_by_group(gid, page=page, search=card.name)
                        group_cards = cards_json.get("data", {}).get("cards", [])
                        if not group_cards:
                            break

                        for c in group_cards[:100]:
                            c_name = norm(c.get("name", ""))
                            c_num = str(c.get("number") or "").strip()

                            if target_num and c_num != target_num:
                                continue

                            pid = c.get("productId") or c.get("productID") or c.get("id")
                            if not pid:
                                continue

                            score = 0
                            if c_name == name_norm:
                                score += 6
                            elif name_norm in c_name:
                                score += 3

                            if target_num and c_num == target_num:
                                score += 10

                            if set_digits and (set_digits & digits(exp_name)):
                                score += 4
                            if set_norm and any(w in norm(exp_name) for w in set_norm.split()):
                                score += 1

                            if best is None or score > best[0]:
                                best = (score, gid, int(pid), exp_name, c.get("name", ""), c_num)

                        if best and target_num and best[5] == target_num:
                            break

                except Exception as e:
                    continue
            if not best or best[0] < 10:
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"Could not link: {card.name} | set='{card.set_name}' | num='{card.card_number}'"
                ))
                continue

            score, gid, pid, exp_name, matched_name, matched_num = best
            card.tcgapis_group_id = gid
            card.tcgapis_product_id = pid
            card.save(update_fields=["tcgapis_group_id", "tcgapis_product_id"])

            linked += 1
            self.stdout.write(self.style.SUCCESS(
                f"Linked {card.name} -> productId={pid} (set='{exp_name}', matched='{matched_name}' #{matched_num}, score={score})"
            ))

        self.stdout.write(f"Done. Linked={linked}, Skipped={skipped}")

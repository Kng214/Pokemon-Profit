from django.core.management.base import BaseCommand, CommandError
from tracker.models import Card
from tracker.services.tcgapis import get_cards_by_group, TcgApisRateLimitError
import time

class Command(BaseCommand):
    help = "Link one Card to TCGAPIs productId by scanning a set (groupId) for an exact card number."

    def add_arguments(self, parser):
        parser.add_argument("card_id", type=int, help="Your Card model ID (pk)")
        parser.add_argument("--max-pages", type=int, default=80)
        parser.add_argument("--sleep", type=float, default=1.0, help="Sleep between page requests (fallback scan)")

    def handle(self, *args, **opts):
        card_id = opts["card_id"]
        max_pages = opts["max_pages"]
        sleep_s = opts["sleep"]

        card = Card.objects.get(pk=card_id)
        if not card.tcgapis_group_id:
            raise CommandError("Card has no tcgapis_group_id. Link the set first.")

        target_num = (card.card_number or "").split("/")[0].strip()
        if not target_num:
            raise CommandError("Card has no card_number to match.")

        gid = card.tcgapis_group_id

        # ✅ Attempt 1: search by number (often works even if docs say name-only)
        for quick_search in [target_num, f"{card.name} {target_num}", card.name]:
            try:
                data = get_cards_by_group(gid, page=1, search=quick_search)
            except TcgApisRateLimitError as e:
                raise CommandError(str(e))

            cards = data.get("data", {}).get("cards", [])
            for c in cards:
                c_num = str(c.get("number") or "").strip()
                if c_num == target_num:
                    pid = c.get("productId") or c.get("productID") or c.get("id")
                    if not pid:
                        raise CommandError("Found matching number but no productId field.")

                    card.tcgapis_product_id = int(pid)
                    card.save(update_fields=["tcgapis_product_id"])

                    self.stdout.write(self.style.SUCCESS(
                        f"Linked Card(pk={card.pk}) {card.name} #{card.card_number} -> "
                        f"productId={card.tcgapis_product_id} (groupId={gid})"
                    ))
                    self.stdout.write(f"Matched API card name: {c.get('name')}")
                    return

        # ✅ Fallback: scan pages without search (slow, but guaranteed if API allows)
        for page in range(1, max_pages + 1):
            try:
                data = get_cards_by_group(gid, page=page)  # no search
            except TcgApisRateLimitError as e:
                raise CommandError(str(e))

            cards = data.get("data", {}).get("cards", [])
            if not cards:
                break

            for c in cards:
                c_num = str(c.get("number") or "").strip()
                if c_num == target_num:
                    pid = c.get("productId") or c.get("productID") or c.get("id")
                    if not pid:
                        raise CommandError("Found matching number but no productId field.")

                    card.tcgapis_product_id = int(pid)
                    card.save(update_fields=["tcgapis_product_id"])

                    self.stdout.write(self.style.SUCCESS(
                        f"Linked Card(pk={card.pk}) {card.name} #{card.card_number} -> "
                        f"productId={card.tcgapis_product_id} (groupId={gid})"
                    ))
                    self.stdout.write(f"Matched API card name: {c.get('name')}")
                    return

            time.sleep(sleep_s)

        raise CommandError(f"Did not find number {target_num} in groupId={gid} after {max_pages} pages.")

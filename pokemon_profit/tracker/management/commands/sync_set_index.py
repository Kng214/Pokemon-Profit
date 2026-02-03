import time
from django.core.management.base import BaseCommand
from tracker.models import TcgApisCardIndex
from tracker.services.tcgapis import get_cards_by_group

class Command(BaseCommand):
    help = "Cache all cards for one groupId locally (number -> productId)."

    def add_arguments(self, parser):
        parser.add_argument("group_id", type=int)
        parser.add_argument("--max-pages", type=int, default=200)
        parser.add_argument("--sleep", type=float, default=0.2)

    def handle(self, *args, **opts):
        gid = opts["group_id"]
        max_pages = opts["max_pages"]
        sleep_s = opts["sleep"]

        created = 0
        updated = 0

        for page in range(1, max_pages + 1):
            data = get_cards_by_group(gid, page=page)  # now rate-limit safe
            cards = data.get("data", {}).get("cards", [])
            if not cards:
                break

            for c in cards:
                num = str(c.get("number") or "").strip()
                pid = c.get("productId") or c.get("productID") or c.get("id")
                if not num or not pid:
                    continue

                _, was_created = TcgApisCardIndex.objects.update_or_create(
                    group_id=gid,
                    number=num,
                    defaults={"product_id": int(pid), "name": (c.get("name") or "")[:255]},
                )
                created += int(was_created)
                updated += int(not was_created)

            time.sleep(sleep_s)

        self.stdout.write(self.style.SUCCESS(
            f"Indexed groupId={gid}. created={created}, updated={updated}"
        ))

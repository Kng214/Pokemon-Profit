import csv
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from tracker.models import CatalogItem, PriceSnapshot


def dec(v):
    try:
        return Decimal(v) if v not in ("", None) else None
    except InvalidOperation:
        return None


def parse_dt(v):
    if not v:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(v)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


class Command(BaseCommand):
    help = "Import products and prices from a TCGCSV export (header-based)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--category-id", type=int)
        parser.add_argument("--group-id", type=int)
        parser.add_argument("--sealed-only", action="store_true")
        parser.add_argument("--singles-only", action="store_true")
        parser.add_argument("--capture-now", action="store_true")

    def handle(self, *args, **opts):
        path = opts["csv_path"]
        category_filter = opts.get("category_id")
        group_filter = opts.get("group_id")
        sealed_only = opts["sealed_only"]
        singles_only = opts["singles_only"]
        capture_now = opts["capture_now"]

        created_items = updated_items = price_rows = skipped = 0

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                product_id = int(row["productId"])
                name = row["name"].strip()
                image_url = row["imageUrl"].strip()
                category_id = int(row["categoryId"]) if row["categoryId"] else None
                group_id = int(row["groupId"]) if row["groupId"] else None

                if category_filter and category_id != category_filter:
                    skipped += 1
                    continue
                if group_filter and group_id != group_filter:
                    skipped += 1
                    continue

                card_number = (row.get("extNumber") or "").strip()
                printing = (row.get("subTypeName") or "Normal").strip()
                rarity = (row.get("extRarity") or "").strip()

                is_single = bool(card_number)
                is_sealed = not is_single

                if sealed_only and not is_sealed:
                    skipped += 1
                    continue
                if singles_only and not is_single:
                    skipped += 1
                    continue

                item, created = CatalogItem.objects.update_or_create(
                    product_id=product_id,
                    printing=printing,
                    defaults={
                        "name": name,
                        "image_url": image_url,
                        "category_id": category_id,
                        "group_id": group_id,
                        "tcgcsv_url": row.get("url", ""),
                        "card_number": card_number,
                        "rarity": rarity,
                        "is_sealed": is_sealed,
                    }
                )

                created_items += int(created)
                updated_items += int(not created)

                captured_at = (
                    datetime.now(timezone.utc)
                    if capture_now
                    else parse_dt(row.get("modifiedOn"))
                )

                if any(row.get(k) for k in ["lowPrice", "midPrice", "highPrice", "marketPrice"]):
                    PriceSnapshot.objects.update_or_create(
                        item=item,
                        captured_at=captured_at,
                        defaults={
                            "low": dec(row.get("lowPrice")),
                            "mid": dec(row.get("midPrice")),
                            "high": dec(row.get("highPrice")),
                            "market": dec(row.get("marketPrice")),
                            "direct_low": dec(row.get("directLowPrice")),
                            "source": "tcgcsv",
                        }
                    )
                    price_rows += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done ✅ items_created={created_items}, items_updated={updated_items}, "
            f"prices_upserted={price_rows}, skipped={skipped}"
        ))

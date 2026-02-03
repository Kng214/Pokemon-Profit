from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from tracker.models import Card, MarketPrice
from tracker.services.pricing import fetch_price_by_product_id, RateLimitError

class Command(BaseCommand):
    help = "Update market prices from TCGAPIs"

    def add_arguments(self, parser):
        parser.add_argument("--card-id", type=int, default=None)
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--stale-hours", type=int, default=24)
        parser.add_argument("--max-wait", type=int, default=60)

    def handle(self, *args, **opts):
        qs = Card.objects.all()

        if opts["card_id"]:
            qs = qs.filter(id=opts["card_id"])

        if opts["limit"]:
            qs = qs[: opts["limit"]]

        stale_cutoff = timezone.now() - timedelta(hours=opts["stale_hours"])
        max_wait = int(opts["max_wait"])

        updated = skipped = errors = rate_limited = 0

        for card in qs:
            if not card.tcgapis_product_id:
                self.stdout.write(f"Skipped {card.name} (no tcgapis_product_id)")
                skipped += 1
                continue

            latest = MarketPrice.objects.filter(card=card).order_by("-date").first()
            if latest and latest.date and latest.date >= stale_cutoff:
                self.stdout.write(f"Skipped {card.name} (fresh price)")
                skipped += 1
                continue

            try:
                price = fetch_price_by_product_id(card.tcgapis_product_id, max_wait_seconds=max_wait)
                if price is None:
                    self.stdout.write(f"No price found for {card.name} (productId={card.tcgapis_product_id})")
                    skipped += 1
                    continue

                MarketPrice.objects.create(card=card, price=price, source="TCGAPIs")
                self.stdout.write(self.style.SUCCESS(f"Updated {card.name}: {price}"))
                updated += 1

            except RateLimitError as e:
                self.stdout.write(self.style.WARNING(f"RATE LIMITED: {card.name} -> {e}"))
                rate_limited += 1
                continue

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"ERROR {card.name}: {e}"))
                errors += 1

        self.stdout.write(
            f"Done. Updated={updated}, Skipped={skipped}, RateLimited={rate_limited}, Errors={errors}"
        )

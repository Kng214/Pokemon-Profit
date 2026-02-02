from django.core.management.base import BaseCommand
from tracker.models import Card, MarketPrice
from tracker.services.tcgapis import get_prices_by_product

class Command(BaseCommand):
    help = "Update market prices from TCGAPIs using stored tcgapis_product_id"

    def handle(self, *args, **options):
        updated, skipped, errors = 0, 0, 0

        for card in Card.objects.all():
            if not card.tcgapis_product_id:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Skipped {card.name} (no tcgapis_product_id)"))
                continue

            try:
                data = get_prices_by_product(card.tcgapis_product_id)

                # Inspect typical structure: {"success":true,"data":{"prices":[...]}}
                prices = data.get("data", {}).get("prices")
                market = None

                # Try some common shapes
                if isinstance(prices, list) and prices:
                    # often first entry is the relevant one; sometimes "marketPrice" exists
                    market = prices[0].get("marketPrice") or prices[0].get("market")

                if market is None and "data" in data:
                    market = data["data"].get("marketPrice")

                if market is None:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"No market price for {card.name}"))
                    continue

                MarketPrice.objects.create(card=card, price=market, source="TCGAPIs")
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"Updated {card.name}: {market}"))

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Error for {card.name}: {e}"))

        self.stdout.write(f"Done. Updated={updated}, Skipped={skipped}, Errors={errors}")

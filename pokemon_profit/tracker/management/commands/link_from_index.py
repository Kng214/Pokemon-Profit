from django.core.management.base import BaseCommand
from tracker.models import Card, TcgApisCardIndex

class Command(BaseCommand):
    help = "Link cards using the local index table (no API calls)."

    def add_arguments(self, parser):
        parser.add_argument("--card-id", type=int, default=None)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        card_id = opts["card_id"]
        force = opts["force"]

        qs = Card.objects.all()
        if card_id is not None:
            qs = qs.filter(pk=card_id)

        linked, skipped = 0, 0

        for card in qs:
            if card.tcgapis_product_id and not force:
                continue
            if not card.tcgapis_group_id:
                skipped += 1
                continue

            target_num = (card.card_number or "").split("/")[0].strip()
            if not target_num:
                skipped += 1
                continue

            idx = TcgApisCardIndex.objects.filter(group_id=card.tcgapis_group_id, number=target_num).first()
            if not idx:
                skipped += 1
                continue

            card.tcgapis_product_id = idx.product_id
            card.save(update_fields=["tcgapis_product_id"])
            linked += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Linked={linked}, Skipped={skipped}"))

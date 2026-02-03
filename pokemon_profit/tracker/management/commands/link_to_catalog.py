from django.core.management.base import BaseCommand
from tracker.models import Card, CardCatalog

class Command(BaseCommand):
    help = "Link owned Cards to CardCatalog using set_name + card_number numerator."

    def add_arguments(self, parser):
        parser.add_argument("--card-id", type=int, default=None)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        qs = Card.objects.all()
        if opts["card_id"] is not None:
            qs = qs.filter(pk=opts["card_id"])

        linked = 0
        skipped = 0
        not_found = 0

        for card in qs:
            if card.catalog_id and not opts["force"]:
                skipped += 1
                continue

            if not card.set_name or not card.card_number:
                skipped += 1
                continue

            num = (card.card_number.split("/", 1)[0]).strip()

            hit = (
                CardCatalog.objects
                .filter(set_name__iexact=card.set_name.strip(), number=num)
                .first()
            )

            if not hit:
                # fallback: loose match (sometimes your set_name differs slightly)
                hit = (
                    CardCatalog.objects
                    .filter(set_name__icontains=card.set_name.strip(), number=num)
                    .first()
                )

            if not hit:
                not_found += 1
                self.stdout.write(self.style.WARNING(
                    f"Not found in catalog: {card.name} set='{card.set_name}' num='{card.card_number}'"
                ))
                continue

            card.catalog = hit
            # Optionally normalize name/set from catalog
            card.name = hit.name
            card.set_name = hit.set_name
            card.card_number = f"{hit.number}/{card.card_number.split('/',1)[1]}" if "/" in card.card_number else hit.number

            card.save()
            linked += 1
            self.stdout.write(self.style.SUCCESS(
                f"Linked Card(id={card.id}) -> Catalog({hit.set_name} #{hit.number} {hit.name})"
            ))

        self.stdout.write(self.style.SUCCESS(f"Done. Linked={linked}, Skipped={skipped}, NotFound={not_found}"))

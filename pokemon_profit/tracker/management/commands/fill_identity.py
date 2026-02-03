from django.core.management.base import BaseCommand
from tracker.models import Card
from tracker.services.pokemontcg import fetch_card_by_set_and_number

class Command(BaseCommand):
    help = "Fill Card identity fields from pokemontcg.io using set_name + card_number."

    def add_arguments(self, parser):
        parser.add_argument("--card-id", type=int, default=None)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        card_id = opts["card_id"]
        force = opts["force"]

        qs = Card.objects.all()
        if card_id is not None:
            qs = qs.filter(pk=card_id)

        updated = 0
        skipped = 0
        not_found = 0

        for card in qs:
            if card.ptcg_id and not force:
                skipped += 1
                continue

            if not card.set_name or not card.card_number:
                skipped += 1
                self.stdout.write(f"Skipped (missing set/number): {card.name}")
                continue

            num = (card.card_number or "").split("/")[0].strip()

            try:
                hit = fetch_card_by_set_and_number(card.set_name, num)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fetching {card.name}: {e}"))
                continue

            if not hit:
                not_found += 1
                self.stdout.write(self.style.WARNING(
                    f"Not found: {card.name} | set='{card.set_name}' num='{card.card_number}'"
                ))
                continue

            images = hit.get("images") or {}
            set_info = hit.get("set") or {}

            card.ptcg_id = hit.get("id")
            card.ptcg_number = hit.get("number")
            card.ptcg_rarity = hit.get("rarity")
            card.ptcg_set_id = set_info.get("id")
            card.ptcg_set_name = set_info.get("name")
            card.ptcg_image_small = images.get("small")
            card.ptcg_image_large = images.get("large")

            # Optionally normalize your fields too:
            card.set_name = card.ptcg_set_name or card.set_name
            if card.ptcg_number:
                # keep your denominator if you want; otherwise just set numerator
                denom = card.card_number.split("/", 1)[1] if "/" in card.card_number else ""
                card.card_number = f"{card.ptcg_number}/{denom}" if denom else str(card.ptcg_number)

            card.save()
            updated += 1
            self.stdout.write(self.style.SUCCESS(
                f"Updated: {card.name} -> ptcg_id={card.ptcg_id} set='{card.ptcg_set_name}' num={card.ptcg_number} rarity={card.ptcg_rarity}"
            ))

        self.stdout.write(f"Done. Updated={updated}, Skipped={skipped}, NotFound={not_found}")

from django.core.management.base import BaseCommand

from config.settings import TINKOFF_TOKEN
from dashboard.models import Share
from dashboard.services.market_data import _client_class


class Command(BaseCommand):
    help = "Add shares from the Tinkoff Invest API to the database"

    def handle(self, *args, **options):
        if not TINKOFF_TOKEN:
            self.stderr.write(
                self.style.ERROR(
                    "TINKOFF_TOKEN is not set; export it before running add_shares."
                )
            )
            return

        Client = _client_class()
        with Client(TINKOFF_TOKEN) as client:
            shares = client.instruments.shares()

        created = 0
        for share in shares.instruments:
            # Look up by figi only: the other fields may legitimately change
            # between API releases and must not turn an update into a duplicate.
            _, was_created = Share.objects.update_or_create(
                figi=share.figi,
                defaults={
                    "name": share.name,
                    "isin": share.isin,
                    "ticker": share.ticker,
                    "currency": share.currency,
                    "uid": share.uid,
                },
            )
            created += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {len(shares.instruments)} instruments ({created} new)."
            )
        )

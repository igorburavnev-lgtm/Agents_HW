from config.celery import app
from config.settings import logger
from dashboard.models import Share
from dashboard.services.market_data import get_last_data


@app.task
def update_last_price():
    """Refresh ``last_price`` / ``is_trend_high`` for every share."""
    for share in Share.objects.all():
        try:
            last_price_data = get_last_data(share)
        except Exception as exc:  # noqa: BLE001 - one broken instrument must not stop the run
            logger.error("Failed to get price for share %s: %s", share.id, exc)
            continue

        if not last_price_data:
            # No quote for this instrument: keep the previous value.
            continue

        last_price = last_price_data[0]
        try:
            if share.last_price is None:
                # Nothing to compare with yet; treat the first quote as growth.
                is_trend_high = True
            else:
                is_trend_high = last_price >= share.last_price
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to compare prices for share %s: %s", share.id, exc)
            continue

        try:
            # ``save()`` (unlike ``QuerySet.update()``) keeps ``updated_at`` accurate.
            share.last_price = last_price
            share.is_trend_high = is_trend_high
            share.save(update_fields=["last_price", "is_trend_high", "updated_at"])
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to save price for share %s: %s", share.id, exc)

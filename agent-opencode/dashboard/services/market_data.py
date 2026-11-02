"""Access to market data provided by the Tinkoff Invest API.

The SDK is optional: importing it lazily keeps ``manage.py check`` and the
test suite working on machines where the package is not installed, while a
real installation is used automatically when present.  A local stub package
must not shadow the real SDK, so this project no longer ships one.
"""

from config.settings import TINKOFF_TOKEN, logger

NANO = 1_000_000_000


def _client_class():
    """Import the real Tinkoff client lazily with an actionable error."""
    try:
        from tinkoff.invest import Client
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError(
            "Tinkoff Invest SDK is not installed. "
            "Install requirements-tinkoff.txt or skip market-data operations."
        ) from exc
    return Client


def quotation_to_float(quotation) -> float:
    """Convert a Tinkoff ``Quotation`` without dropping its ``nano`` part."""
    return quotation.units + quotation.nano / NANO


def get_last_data(share):
    """Return ``[last_price, price_time]`` for ``share`` or ``None``.

    ``None`` means the API answered successfully but had no quote for the
    instrument; callers can then keep the previous stored price.
    """
    if not TINKOFF_TOKEN:
        raise ValueError("TINKOFF_TOKEN is not set")

    Client = _client_class()
    with Client(TINKOFF_TOKEN) as client:
        response = client.market_data.get_last_prices(figi=[share.figi])

    if not response.last_prices:
        return None

    price_info = response.last_prices[0]
    logger.info("Get last data for share with id %s", share.id)
    return [quotation_to_float(price_info.price), price_info.time]

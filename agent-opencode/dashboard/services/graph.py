"""Building the price chart shown on the share detail page."""

from datetime import timedelta

from plotly.graph_objs import Scatter
from plotly.offline import plot

from config.settings import TINKOFF_TOKEN
from dashboard.services.market_data import _client_class, quotation_to_float


def get_graph(share):
    """Return a Plotly ``<div>`` with daily candles for the last 180 days."""
    if not TINKOFF_TOKEN:
        raise ValueError("TINKOFF_TOKEN is not set")

    from tinkoff.invest import CandleInterval
    from tinkoff.invest.utils import now

    Client = _client_class()
    x_data, y_data = [], []
    with Client(TINKOFF_TOKEN) as client:
        for candle in client.get_all_candles(
            figi=share.figi,
            from_=now() - timedelta(days=180),
            interval=CandleInterval.CANDLE_INTERVAL_DAY,
        ):
            x_data.append(candle.time.date())
            y_data.append(quotation_to_float(candle.close))

    return plot(
        [
            Scatter(
                x=x_data,
                y=y_data,
                mode="lines",
                name=share.ticker,
                opacity=0.8,
                marker_color="red",
            )
        ],
        output_type="div",
        show_link=False,
        link_text="",
        # Plotly.js is already loaded from the CDN in base.html.
        include_plotlyjs=False,
    )

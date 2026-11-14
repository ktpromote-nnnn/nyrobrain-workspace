import polars as pl
from typing import override

from adrs import Alpha
from adrs.data import DataInfo, DataColumn, DataProcessor


class FundingRateMomentum(Alpha):
    def __init__(self, lookback: int, vol_window: int, entry: float) -> None:
        super().__init__(
            id="btc_funding_rate_momentum",
            data_infos=[
                DataInfo(
                    topic="cryptoquant|btc/market-data/funding-rates?window=day&exchange=all_exchange",
                    columns=[DataColumn(src="funding_rates", dst="funding_rate")],
                    lookback_size=lookback + vol_window + 100,
                ),
            ],
            data_processor=DataProcessor(),
        )
        self.lookback = lookback
        self.vol_window = vol_window
        self.entry = entry

    @override
    def next(self, data_df: pl.DataFrame) -> pl.DataFrame:
        # Daily funding is an end-of-day aggregate: use the prior day's value
        # so the signal only contains information available before the bar.
        funding = pl.col("funding_rate").shift(1)
        change = funding - funding.shift(self.lookback)
        zscore = change / change.rolling_std(self.vol_window, ddof=1)

        df = data_df.with_columns(zscore.alias("funding_momentum_z"))
        df = df.with_columns(
            pl.when(pl.col("funding_momentum_z") >= self.entry)
            .then(1.0)
            .when(pl.col("funding_momentum_z") <= -self.entry)
            .then(-1.0)
            .otherwise(None)
            .forward_fill()
            .fill_null(0.0)
            .alias("signal")
        )
        return df

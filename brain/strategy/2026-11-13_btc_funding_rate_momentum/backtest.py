import os
import asyncio
from pathlib import Path
from datetime import datetime
from adrs.data import DataInfo, DataColumn, DataLoader, make_datamap
from adrs.utils import backforward_split
from adrs.performance import Evaluator
from adrs.logging import setup_logger
from adrs.report import AlphaReportV1

from alpha import FundingRateMomentum


def _find_project_root(marker: str = "pyproject.toml") -> Path:
    p = Path(__file__).resolve()
    for parent in [p, *p.parents]:
        if (parent / marker).exists():
            return parent
    raise RuntimeError(f"{marker} not found above {__file__}")


PROJECT_ROOT = _find_project_root()


async def main():
    setup_logger()

    start_time = datetime.fromisoformat("2020-04-01T00:00:00Z")
    end_time = datetime.fromisoformat("2026-11-11T00:00:00Z")

    dataloader = DataLoader(
        data_dir=os.environ["NYROBRAIN_DATA_DIR"],
        credentials={"cybotrade_api_key": os.environ["USER_ID"]},
        cybotrade_api_url=os.environ["DATASOURCE_PROXY_URL"],
    )
    evaluator = Evaluator(
        assets={
            "BTC": DataInfo(
                topic="bybit-linear|candle?symbol=BTCUSDT&interval=1h",
                columns=[DataColumn(src="close", dst="price")],
                lookback_size=0,
            )
        }
    )
    alpha = FundingRateMomentum(lookback=30, vol_window=90, entry=0.5)

    datamap = await make_datamap(
        dataloader=dataloader,
        start_time=start_time,
        end_time=end_time,
        data_infos=alpha.data_infos,
        evaluator=evaluator,
    )

    data_df = alpha.data_processor.process(datamap)

    B_start, B_end, F_start, F_end = backforward_split(
        start_time=start_time, end_time=end_time, size=(0.7, 0.3)
    )
    report = AlphaReportV1.compute(
        alpha,
        B_start,
        B_end,
        F_start,
        F_end,
        evaluator=evaluator,
        base_asset="BTC",
        datamap=datamap,
        data_df=data_df,
        fees=0.035,
        price_shift=1,
    )
    print("backtest", report.back.performance)
    print("forward test", report.forward.performance)
    REPORT_COLS = ["start_time", "price", "signal", "pnl"]
    report.back.performance_df = report.back.performance_df.select(REPORT_COLS)
    report.forward.performance_df = report.forward.performance_df.select(REPORT_COLS)
    report.write_parquet(str(Path(__file__).parent / "report.parquet"))


if __name__ == "__main__":
    asyncio.run(main())

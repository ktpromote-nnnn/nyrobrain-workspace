"""
Generate visualization plots from an AlphaReportV1 parquet file for the
back/forward 73-split pipeline.

Copy this file verbatim into the strategy directory — it reads
`report.parquet` from its own directory and writes to `./assets/`.

Usage (from anywhere):
    uv run python path/to/strategy/plot.py
"""

from pathlib import Path

import io
import numpy as np
import polars as pl
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


STRATEGY_DIR = Path(__file__).resolve().parent


def load_report(strategy_dir: Path):
    # New backtests write `report.parquet`; older strategies on disk may
    # still have `report.parquet.png` from a prior fs-encoding workaround.
    report_path = strategy_dir / "report.parquet"
    if not report_path.exists():
        legacy = strategy_dir / "report.parquet.png"
        if legacy.exists():
            report_path = legacy
    df = pl.read_parquet(report_path)
    row = df.row(0, named=True)
    back_df = pl.read_parquet(io.BytesIO(row["back_pdf_buf"]))
    forward_df = pl.read_parquet(io.BytesIO(row["forward_pdf_buf"]))
    full_df = pl.concat([back_df, forward_df])
    split_time = back_df["start_time"][-1]
    return full_df, split_time


def plot_equity_curve(full_df: pl.DataFrame, split_time, out: Path):
    times = full_df["start_time"].to_list()
    equity = full_df["pnl"].cum_sum().to_numpy()

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(times, equity, linewidth=0.6, color="#c0392b")
    ax.axvline(
        x=split_time,
        color="#2c3e50",
        linestyle="--",
        linewidth=1,
        label="Back/Forward Split",
    )
    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.4, alpha=0.5)
    ax.set_title("Equity Curve (Arithmetic Returns)")
    ax.set_ylabel("Cumulative Return")
    ax.legend()
    ax.grid(True, alpha=0.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def plot_rolling_sharpe(full_df: pl.DataFrame, split_time, out: Path):
    times = full_df["start_time"].to_list()
    pnl = full_df["pnl"]

    roll_30d = 30  # 30 days in daily bars
    roll_180d = 180  # 180 days in daily bars
    ann_factor = np.sqrt(365)

    sharpe_30d = (
        (pnl.rolling_mean(roll_30d) / pnl.rolling_std(roll_30d)) * ann_factor
    ).to_numpy()
    sharpe_180d = (
        (pnl.rolling_mean(roll_180d) / pnl.rolling_std(roll_180d)) * ann_factor
    ).to_numpy()

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(
        times,
        sharpe_30d,
        linewidth=0.7,
        color="#e67e22",
        alpha=0.8,
        label="30d Rolling Sharpe",
    )
    ax.plot(
        times, sharpe_180d, linewidth=1.2, color="#2980b9", label="180d Rolling Sharpe"
    )
    ax.axvline(
        x=split_time,
        color="#2c3e50",
        linestyle="--",
        linewidth=1,
        label="Back/Forward Split",
    )
    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.4, alpha=0.5)
    ax.set_title("Rolling Sharpe Ratio (Annualized)")
    ax.set_ylabel("Sharpe Ratio")
    ax.set_ylim(-5, 5)
    ax.legend()
    ax.grid(True, alpha=0.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def plot_returns_distribution(full_df: pl.DataFrame, out: Path):
    pnl = full_df["pnl"].to_numpy()
    prev_signal = full_df["signal"].shift(1).fill_null(0).to_numpy()
    active_pnl = pnl[prev_signal != 0]
    active_pnl = active_pnl[np.isfinite(active_pnl)]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.hist(active_pnl, bins=200, color="#2c3e50", alpha=0.7, edgecolor="none")
    ax.axvline(
        x=np.mean(active_pnl),
        color="#c0392b",
        linestyle="--",
        linewidth=1.2,
        label=f"Mean: {np.mean(active_pnl):.6f}",
    )
    ax.axvline(
        x=np.median(active_pnl),
        color="#2980b9",
        linestyle="--",
        linewidth=1.2,
        label=f"Median: {np.median(active_pnl):.6f}",
    )
    ax.set_title("PnL Distribution (Active Positions Only)")
    ax.set_xlabel("Daily PnL")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def plot_monthly_returns(full_df: pl.DataFrame, out: Path):
    monthly = (
        full_df.with_columns(
            pl.col("start_time").dt.year().alias("year"),
            pl.col("start_time").dt.month().alias("month"),
        )
        .group_by("year", "month")
        .agg(pl.col("pnl").sum().alias("monthly_return"))
        .sort("year", "month")
    )

    years = sorted(monthly["year"].unique().to_list())
    month_labels = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    matrix = np.full((len(years), 12), np.nan)
    for row in monthly.iter_rows(named=True):
        yi = years.index(row["year"])
        mi = row["month"] - 1
        matrix[yi, mi] = row["monthly_return"] * 100

    fig, ax = plt.subplots(figsize=(14, 4))
    vmax = np.nanmax(np.abs(matrix))
    im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto", vmin=-vmax, vmax=vmax)

    ax.set_xticks(range(12))
    ax.set_xticklabels(month_labels)
    ax.set_yticks(range(len(years)))
    ax.set_yticklabels(years)

    for i in range(len(years)):
        for j in range(12):
            val = matrix[i, j]
            if not np.isnan(val):
                color = "white" if abs(val) > vmax * 0.6 else "black"
                ax.text(
                    j,
                    i,
                    f"{val:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=color,
                    fontweight="bold",
                )

    ax.set_title("Monthly Returns (%)")
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("Return (%)")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def plot_drawdown(full_df: pl.DataFrame, split_time, out: Path):
    times = full_df["start_time"].to_list()
    pnl = full_df["pnl"].to_numpy()
    cumulative = np.cumsum(pnl)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(times, drawdown, 0, color="#c0392b", alpha=0.4)
    ax.plot(times, drawdown, linewidth=0.5, color="#c0392b")
    ax.axvline(
        x=split_time,
        color="#2c3e50",
        linestyle="--",
        linewidth=1,
        label="Back/Forward Split",
    )
    ax.set_title("Drawdown")
    ax.set_ylabel("Drawdown (Arithmetic)")
    ax.legend()
    ax.grid(True, alpha=0.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def main():
    assets_dir = STRATEGY_DIR / "assets"
    assets_dir.mkdir(exist_ok=True)

    full_df, split_time = load_report(STRATEGY_DIR)

    plot_equity_curve(full_df, split_time, assets_dir / "equity_curve.png")
    print("  equity_curve.png")

    plot_rolling_sharpe(full_df, split_time, assets_dir / "rolling_sharpe.png")
    print("  rolling_sharpe.png")

    plot_returns_distribution(full_df, assets_dir / "returns_distribution.png")
    print("  returns_distribution.png")

    plot_monthly_returns(full_df, assets_dir / "monthly_returns.png")
    print("  monthly_returns.png")

    plot_drawdown(full_df, split_time, assets_dir / "drawdown.png")
    print("  drawdown.png")

    print(f"Done. Plots saved to {assets_dir}/")


if __name__ == "__main__":
    main()

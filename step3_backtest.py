"""Step 3: turn a signal into a portfolio and its monthly returns. (Lecture 10)

At the end of each month t, for one strategy file:

    1. compute the signal for every stock
    2. leave out microcaps: stocks below the 20th percentile of NYSE
       market caps
    3. sort the rest into groups on the signal, with the group boundaries set
       by NYSE stocks (10 groups = deciles)
    4. hold the top group, and short the bottom group if the strategy is
       long-short, weighting by market cap or equally
    5. earn the portfolio's return over month t+1, less trading costs

The signal belongs to month t and the return to month t+1. This file is the
only place that pairs them, so you never shift returns yourself.

form_portfolios() runs these steps in order; each has its own function below.
run.py calls this step, then steps 4 and 5. To run it on its own:

    uv run step3_backtest.py examples/gross_profitability.py
"""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
MICROCAP = 0.20   # drop stocks below this percentile of NYSE market caps
COST = 0.002      # trading cost: 0.2% of every dollar bought or sold
WORDS = 180       # the longest DESCRIPTION the factsheet has room for


def load_strategy(path):
    """Read a strategy file: its settings and its signal() function."""
    if not (Path(path).is_file() and Path(path).suffix == ".py"):
        raise SystemExit(f"No strategy file {path}: check the name, as in "
                         "my_strategy.py.")
    spec = importlib.util.spec_from_file_location("strategy", path)
    strategy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(strategy)
    for setting in ["NAME", "OBJECTIVE", "DESCRIPTION", "LONG_SHORT", "GROUPS",
                    "WEIGHTS", "signal"]:
        if not hasattr(strategy, setting):
            raise SystemExit(f"{path} has no {setting}.")
    if strategy.WEIGHTS not in ["value", "equal"]:
        raise SystemExit(f'{path}: WEIGHTS must be "value" or "equal".')
    if strategy.GROUPS < (2 if strategy.LONG_SHORT else 1):
        raise SystemExit(f"{path}: GROUPS is too small for this strategy.")
    words = len(strategy.DESCRIPTION.split())
    if words > WORDS:
        raise SystemExit(f"{path}: DESCRIPTION has {words} words, and the "
                         f"factsheet has room for {WORDS}.")
    return strategy


# [slide: load stocks]
def load_stocks():
    """The monthly table of stocks that step 2 made."""
    path = HERE / "data" / "stocks.parquet"
    if not path.exists():
        raise SystemExit("No data yet: run step 1, then step 2.")
    return pd.read_parquet(path)
# [end]


def add_signal(stocks, strategy):
    """Each stock's signal at the end of month t, checked before it is used."""
    # pass a copy, so that signal() cannot change the data
    signal = strategy.signal(stocks.copy())
    ok = isinstance(signal, pd.Series) and signal.index.equals(stocks.index)
    if not ok:
        raise SystemExit("signal() must return one value per row of stocks.")
    signal = signal.astype(float)
    if np.isinf(signal).any():
        raise SystemExit("signal() gave infinite values (often a division by "
                         "zero). Return NaN for those stocks instead.")
    return stocks.assign(signal=signal)


# [slide: next return]
def add_next_return(stocks):
    """Pair each stock's row for month t with its return over month t+1."""
    following = stocks[["permno", "month", "ret"]].copy()
    # file each return under the month before it, then join on stock and month
    following["month"] = following["month"] - 1
    following = following.rename(columns={"ret": "next_return"})
    return stocks.merge(following, on=["permno", "month"], how="left")
# [end]


def drop_microcaps(stocks):
    """Leave out stocks below the 20th percentile of NYSE market caps."""
    nyse = stocks[stocks["exchange"] == "NYSE"]
    cutoff = nyse.groupby("month")["market_cap"].quantile(MICROCAP)
    return stocks[stocks["market_cap"] >= stocks["month"].map(cutoff)]


def assign_groups(stocks, groups):
    """Each month, sort stocks into groups on their signal: 1 is the lowest.

    The boundaries between groups are set by NYSE stocks alone, as on Ken
    French's website, so the many small NASDAQ stocks don't set them."""
    cuts = [k / groups for k in range(1, groups)]   # deciles: 0.1, ..., 0.9
    group = pd.Series(np.nan, index=stocks.index)
    for month, rows in stocks.groupby("month"):
        nyse = rows.loc[rows["exchange"] == "NYSE", "signal"]
        bounds = nyse.quantile(cuts).to_numpy()
        if np.isnan(bounds).any():      # no NYSE stock has a signal
            continue
        # a stock's group is one more than the number of boundaries below it
        group[rows.index] = 1 + np.searchsorted(bounds, rows["signal"])
    stocks = stocks.assign(group=group).dropna(subset=["group"])
    stocks = stocks.astype({"group": int})
    # Ties can leave the top group empty: a yes-or-no signal fills two groups
    filled = stocks.groupby("month")["group"].agg(lambda g: {1, groups} <= set(g))
    if not filled.all():
        raise SystemExit(f"The signal has too few different values to fill "
                         f"{groups} groups: in {(~filled).sum()} of "
                         f"{len(filled)} months the top or bottom group is "
                         "empty. Lower GROUPS, or use a signal with more "
                         "values.")
    return stocks


def add_weights(stocks, weights):
    """Each stock's weight in its group: by market cap, or equal."""
    if weights == "value":
        size = stocks["market_cap"]
    else:
        size = pd.Series(1.0, index=stocks.index)
    total = size.groupby([stocks["month"], stocks["group"]]).transform("sum")
    return stocks.assign(weight=size / total)


# Each group's return over month t+1 is the weighted average of its stocks'
# returns: r_P = sum of w_i r_i, for every month t and every group g. The
# lines between the markers are the ones shown in Lecture 10.
# [slide: portfolio return]
def group_returns(stocks):
    """r_P = sum of w_i r_i."""
    w = stocks["weight"]
    r = stocks["next_return"]
    t = stocks["month"]
    g = stocks["group"]
    wr = w * r
    r_P = wr.groupby([t, g]).sum()
    return r_P.unstack()
# [end]


def turnover(stocks, group):
    """The share of one group's value bought or sold at each rebalance.

    Between rebalances each weight drifts with its stock's return. Turnover
    adds up |new weight - drifted weight| over all stocks, leavers included."""
    held = stocks[stocks["group"] == group]
    grown = held["weight"] * (1 + held["next_return"])
    drifted = held[["permno", "month"]].assign(
        month=held["month"] + 1,                  # where it stands a month on
        drifted=grown / grown.groupby(held["month"]).transform("sum"))
    new = held[["permno", "month", "weight"]]
    both = new.merge(drifted, on=["permno", "month"], how="outer")
    both = both[both["month"].isin(new["month"])]
    both = both.fillna({"weight": 0, "drifted": 0})
    change = (both["weight"] - both["drifted"]).abs()
    return change.groupby(both["month"]).sum()


# [slide: recipe]
def form_portfolios(stocks, strategy):
    """The steps at the top of this file, in order. Returns three tables."""
    stocks = add_signal(stocks, strategy)
    stocks = add_next_return(stocks)
    stocks = drop_microcaps(stocks)
    # A stock with no return next month is left out. That is rare, because
    # CRSP folds a delisted stock's final return into its last month.
    stocks = stocks.dropna(subset=["signal", "next_return"])
    stocks = assign_groups(stocks, strategy.GROUPS)
    stocks = add_weights(stocks, strategy.WEIGHTS)
    # [end]

    # [slide: long short]
    groups = group_returns(stocks)
    top, bottom = strategy.GROUPS, 1
    if strategy.LONG_SHORT:             # buy the top group, short the bottom
        legs = [top, bottom]
        gross = groups[top] - groups[bottom]
    else:                               # buy the top group only
        legs = [top]
        gross = groups[top]
    traded = sum(turnover(stocks, leg) for leg in legs)
    returns = pd.DataFrame({"gross": gross, "turnover": traded})
    returns["cost"] = COST * returns["turnover"]
    returns["net"] = returns["gross"] - returns["cost"]
    # [end]

    # label each return by the month it was earned, t+1; holdings stay at t
    returns.index = returns.index + 1
    groups.index = groups.index + 1
    holdings = stocks[stocks["group"].isin(legs)]
    return returns, groups, holdings


def check():
    """Check the steps above on four made-up stocks, worked by hand."""
    jan, feb, mar = pd.period_range("2000-01", periods=3, freq="M")
    stocks = pd.DataFrame({
        "permno": [1, 2, 3, 4] * 3,
        "month": [jan] * 4 + [feb] * 4 + [mar] * 4,
        "exchange": "NYSE",
        "market_cap": [20, 20, 30, 20] + [20] * 8,
        "ret": [0.5] * 4 + [0.10, -0.10, 0.05, 0.20] + [0, 0.10, 0, 0],
        "x": [1, 2, 3, 4] + [1, 2, 4, 3] + [1, 2, 3, 4],
    })
    # a strategy written on the spot: long-short, two groups, signal = x
    strategy = SimpleNamespace(GROUPS=2, WEIGHTS="value", LONG_SHORT=True,
                               signal=lambda stocks: stocks["x"])
    returns, groups, holdings = form_portfolios(stocks, strategy)
    # January: stocks 1-2 low, 3-4 high; February's returns, value-weighted
    assert np.allclose(groups.loc[feb], [0.0, 0.6 * 0.05 + 0.4 * 0.20])
    assert np.allclose(groups.loc[mar], [0.05, 0.0])
    assert np.allclose(returns["gross"], [0.11, -0.05])
    # all bought in January; in February only the drift is traded back
    drift = abs(0.5 - 0.6 * 1.05 / 1.11) + abs(0.5 - 0.4 * 1.20 / 1.11)
    assert np.allclose(returns["turnover"], [2.0, drift + 0.10])
    cost = COST * returns["turnover"]
    assert np.allclose(returns["net"], returns["gross"] - cost)
    assert len(holdings) == 8


def save(name, returns, groups, holdings):
    """Write the three tables to results/<name>/ as CSV files."""
    folder = HERE / "results" / name
    folder.mkdir(parents=True, exist_ok=True)
    returns.to_csv(folder / "returns.csv", index_label="month")
    groups.to_csv(folder / "groups.csv", index_label="month")
    columns = ["month", "permno", "ticker", "name", "industry", "market_cap",
               "signal", "group", "weight"]
    holdings[columns].to_csv(folder / "holdings.csv", index=False)
    return folder


if __name__ == "__main__":
    check()
    path = sys.argv[1] if len(sys.argv) > 1 else "my_strategy.py"
    strategy = load_strategy(path)
    returns, groups, holdings = form_portfolios(load_stocks(), strategy)
    folder = save(Path(path).stem, returns, groups, holdings)
    print(f"{strategy.NAME}: {len(returns)} months, "
          f"{returns.index[0]} to {returns.index[-1]}")
    print(f"  average return {returns['gross'].mean():.2%} a month before "
          f"costs, {returns['net'].mean():.2%} after")
    print(f"  average turnover {returns['turnover'].mean():.0%} a month")
    print(f"  tables in {folder.relative_to(HERE)}/")

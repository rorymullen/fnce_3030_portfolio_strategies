"""Step 4: measure how the strategy did. (Lecture 11)

From step 3's monthly returns and holdings, it works out:

    returns    over 1, 3, 5 and 10 years and each calendar year, before and
               after trading costs, beside the benchmark's
    risk       volatility, the Sharpe ratio, the worst drawdown, beta
    alpha      against the CAPM, the Fama-French three-factor model and the
               five-factor model with momentum, each with its t-statistic
    style      each side's mix of style portfolios (large or small, value,
               blend or growth, and T-bills), with its R-squared
    holdings   industry weights, the largest positions, turnover

Every table is saved as a CSV in results/<strategy>/, so you can open it in
Excel.

evaluate() runs the measurements in order; each has its own function below.
run.py calls step 3, then this step, then step 5. To run it on its own:

    uv run step4_evaluate.py examples/gross_profitability.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.optimize import minimize

from step3_backtest import load_stocks, load_strategy

HERE = Path(__file__).parent

# [slide: models]
# The three factor models, as regression formulas: the strategy's excess return
# on the factors' returns. The intercept is the model's alpha.
MODELS = {
    "CAPM": "excess ~ mktrf",
    "Fama-French 3": "excess ~ mktrf + smb + hml",
    "Fama-French 5 + momentum": "excess ~ mktrf + smb + hml + rmw + cma + umd",
}
# [end]

# The periods the factsheet's return table covers, in months.
PERIODS = {"1 year": 12, "3 years": 36, "5 years": 60, "10 years": 120}

# The style portfolios for style analysis: Ken French's six portfolios of
# stocks sorted by size (large or small) and P/E (value: low P/E; growth: high
# P/E; blend: in between), and T-bills.
STYLES = ["large value", "large blend", "large growth",
          "small value", "small blend", "small growth", "T-bills"]


def load_factors():
    """The monthly factor returns step 1 downloaded, one row per month."""
    path = HERE / "data" / "factors.csv"
    if not path.exists():
        raise SystemExit("No factor data yet: run step 1.")
    factors = pd.read_csv(path)
    factors["month"] = pd.PeriodIndex(factors["month"], freq="M")
    return factors.set_index("month")


def load_results(name):
    """Step 3's monthly returns and holdings for one strategy."""
    folder = HERE / "results" / name
    if not (folder / "returns.csv").exists():
        raise SystemExit(f"No results for {name} yet: run step 3 first.")
    returns = pd.read_csv(folder / "returns.csv")
    returns["month"] = pd.PeriodIndex(returns["month"], freq="M")
    holdings = pd.read_csv(folder / "holdings.csv")
    holdings["month"] = pd.PeriodIndex(holdings["month"], freq="M")
    return returns.set_index("month"), holdings


def load_styles(factors):
    """The style portfolios' monthly returns: the six step 1 downloaded, and
    T-bills (the factor file's risk-free rate)."""
    path = HERE / "data" / "styles.csv"
    if not path.exists():
        raise SystemExit("No style portfolios yet: run step 1.")
    styles = pd.read_csv(path)
    styles["month"] = pd.PeriodIndex(styles["month"], freq="M")
    styles = styles.set_index("month")
    styles["T-bills"] = factors["rf"]
    return styles[STYLES].dropna()


def load_sides(name, strategy):
    """Each side's monthly return before costs, from step 3's group returns:
    the long side (the top group) and, if long-short, the short side (the
    bottom group)."""
    groups = pd.read_csv(HERE / "results" / name / "groups.csv")
    groups["month"] = pd.PeriodIndex(groups["month"], freq="M")
    groups = groups.set_index("month")
    sides = pd.DataFrame({"long": groups[str(strategy.GROUPS)]})
    if strategy.LONG_SHORT:
        sides["short"] = groups["1"]
    return sides


def add_excess_return(returns, factors, long_short):
    """The strategy's monthly return after costs, beside the factors.

    A long-short strategy puts no money down, so its return is already an
    excess return; a long-only strategy's is its return less the T-bill
    rate."""
    data = factors.join(returns["net"], how="inner")
    data["excess"] = data["net"] if long_short else data["net"] - data["rf"]
    return data


# [slide: summary]
def summary(net, excess):
    """Average return, volatility and Sharpe ratio (a year); worst drawdown."""
    wealth = (1 + net).cumprod()                   # what $1 has grown to
    drawdown = wealth / wealth.cummax() - 1        # fall from the last peak
    trough = drawdown.idxmin()
    return {"average return": 12 * net.mean(),
            "volatility": np.sqrt(12) * net.std(),
            "Sharpe ratio": np.sqrt(12) * excess.mean() / excess.std(),
            "worst drawdown": drawdown.min(),
            "drawdown from": wealth[:trough].idxmax(),
            "drawdown to": trough}
# [end]


# The alpha of one factor model: the intercept of a regression of the
# strategy's excess return on the factors' returns, and its t-statistic. The
# lines between the markers are the ones shown in Lecture 11.
# [slide: alpha]
def alpha(model, df):
    """alpha and t-statistic."""
    fit = smf.ols(model, df).fit()
    a = fit.params["Intercept"]
    t = fit.tvalues["Intercept"]
    return a, t, fit.params
# [end]


def alphas(data):
    """Each model's alpha (a year), its t-statistic and the factor loadings."""
    rows = []
    for name, model in MODELS.items():
        a, t, params = alpha(model, data)
        loadings = params.drop("Intercept").to_dict()
        rows.append({"model": name, "alpha": 12 * a, "t": t, **loadings})
    return pd.DataFrame(rows).set_index("model")


# Style analysis (William Sharpe's): the mix of style portfolios whose returns
# track one side's returns most closely. Funds cannot short, so the weights are
# zero or more and sum to 100%: a complete asset allocation. The R-squared is
# the share of the side's return variability that its style explains; the
# intercept is the average return the mix misses, the contribution of picking
# stocks within the styles.
def style_analysis(r, styles):
    """One side's weights on the style portfolios, intercept (a month) and
    R-squared."""
    data = styles.join(r.rename("r"), how="inner")
    X, y = data[STYLES].to_numpy(), data["r"].to_numpy()
    n = len(STYLES)

    def missed_variance(w):            # the variance of what the mix misses
        return np.var(y - X @ w)

    fit = minimize(missed_variance, np.full(n, 1 / n), method="SLSQP",
                   bounds=[(0, 1)] * n,                    # zero or more
                   constraints={"type": "eq",              # sum to 100%
                                "fun": lambda w: w.sum() - 1},
                   options={"ftol": 1e-15, "maxiter": 1000})
    if not fit.success:
        raise RuntimeError(f"Style analysis did not converge: {fit.message}")
    missed = y - X @ fit.x
    return (pd.Series(fit.x, index=STYLES), missed.mean(),
            1 - missed.var() / y.var())


def styles_table(sides, styles):
    """Style analysis of each side: its weights, its intercept (a year) and
    its R-squared."""
    rows = {}
    for side, r in sides.items():
        w, a, r2 = style_analysis(r, styles)
        rows[side] = {**w.to_dict(), "intercept": 12 * a, "R-squared": r2}
    return pd.DataFrame(rows).T


def annualized(r):
    """The average compound return a year over the months in r."""
    return (1 + r).prod() ** (12 / len(r)) - 1


def period_returns(gross, net, market):
    """The average compound return a year over the last 1, 3, 5 and 10
    years and since the start: before costs, after costs, and the market's.
    A period longer than the history is left blank."""
    table = {}
    for label, r in {"before costs": gross, "after costs": net,
                     "market": market}.items():
        row = {period: annualized(r.iloc[-months:]) if len(r) >= months
               else np.nan for period, months in PERIODS.items()}
        row["since start"] = annualized(r)
        table[label] = row
    return pd.DataFrame(table).T


def calendar_years(r):
    """The return in each calendar year."""
    return (1 + r).groupby(r.index.year).prod() - 1


def industry_weights(holdings, stocks, strategy):
    """Each side's weight in each industry at the last rebalance, beside the
    market's (every stock, weighted by market cap, the same month)."""
    month = holdings["month"].max()
    now = holdings[holdings["month"] == month]
    long = now[now["group"] == strategy.GROUPS]
    table = {"long": long.groupby("industry")["weight"].sum()}
    if strategy.LONG_SHORT:
        short = now[now["group"] == 1]
        table["short"] = short.groupby("industry")["weight"].sum()
    market = stocks[stocks["month"] == month]
    caps = market.groupby("industry")["market_cap"].sum()
    table["market"] = caps / caps.sum()
    return pd.DataFrame(table).fillna(0).sort_values("market", ascending=False)


def top_holdings(holdings, strategy, n=10):
    """The n largest positions on each side at the last rebalance."""
    now = holdings[holdings["month"] == holdings["month"].max()]
    sides = {"long": strategy.GROUPS}
    if strategy.LONG_SHORT:
        sides["short"] = 1
    tables = []
    for side, group in sides.items():
        top = now[now["group"] == group].nlargest(n, "weight")
        tables.append(top.assign(side=side))
    return pd.concat(tables)[["side", "ticker", "name", "industry", "weight"]]


def evaluate(name, strategy):
    """The measurements above, in order, for one strategy: the tables."""
    returns, holdings = load_results(name)
    factors = load_factors()
    data = add_excess_return(returns, factors, strategy.LONG_SHORT)
    market = data["mktrf"] + data["rf"]
    gross = returns["gross"].reindex(data.index)
    perf = pd.DataFrame({
        "strategy": summary(data["net"], data["excess"]),
        "market": summary(market, data["mktrf"]),
    })
    return {"summary": perf,
            "alphas": alphas(data),
            "style": styles_table(load_sides(name, strategy), load_styles(factors)),
            "periods": period_returns(gross, data["net"], market),
            "calendar": pd.DataFrame({"before costs": calendar_years(gross),
                                      "after costs": calendar_years(data["net"]),
                                      "market": calendar_years(market)}),
            "industries": industry_weights(holdings, load_stocks(), strategy),
            "top_holdings": top_holdings(holdings, strategy)}


def check():
    """Check the measurements on made-up returns, worked by hand."""
    months = pd.period_range("2000-01", periods=6, freq="M")
    # a path that rises 10%, halves, then rises 20%: the worst drawdown is -50%
    s = summary(pd.Series([0.1, -0.5, 0.2, 0, 0, 0], index=months),
                pd.Series([0.1, -0.5, 0.2, 0, 0, 0], index=months))
    assert np.isclose(s["worst drawdown"], -0.5)
    assert s["drawdown from"] == months[0] and s["drawdown to"] == months[1]
    # 1% a month for two years compounds to 1.01^12 - 1 = 12.68% a year; the
    # last year alone, and the five-year column, which has no data, is blank
    r = pd.Series(0.01, index=pd.period_range("2000-01", periods=24, freq="M"))
    t = period_returns(r, r, r)
    assert np.isclose(t.loc["after costs", "since start"], 1.01 ** 12 - 1)
    assert np.isclose(t.loc["market", "1 year"], 1.01 ** 12 - 1)
    assert np.isnan(t.loc["before costs", "5 years"])
    # a strategy built as 0.2% a month plus 1.5 times the market, plus a little
    # noise: the CAPM regression finds the 0.2% and the 1.5 again
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"mktrf": rng.normal(0.01, 0.04, 240)})
    df["excess"] = 0.002 + 1.5 * df["mktrf"] + rng.normal(0, 0.0001, 240)
    a, t, params = alpha(MODELS["CAPM"], df)
    assert np.isclose(a, 0.002, atol=1e-4) and t > 10
    assert np.isclose(params["mktrf"], 1.5, atol=1e-3)
    # style analysis: a side built as 0.1% a month plus 60% large value and 40%
    # T-bills finds the 60/40 mix, the 0.1% and an R-squared of 1
    styles = pd.DataFrame(rng.normal(0.01, 0.05, (240, len(STYLES))),
                          columns=STYLES)
    r = 0.001 + 0.6 * styles["large value"] + 0.4 * styles["T-bills"]
    w, a, r2 = style_analysis(r, styles)
    assert np.allclose(w[["large value", "T-bills"]], [0.6, 0.4], atol=1e-4)
    assert np.isclose(a, 0.001, atol=1e-5) and np.isclose(r2, 1)
    # a side that is short small growth still gets weights of zero or more
    # that sum to 100%
    w, a, r2 = style_analysis(1.5 * styles["large value"]
                              - 0.5 * styles["small growth"], styles)
    assert (w >= -1e-9).all() and np.isclose(w.sum(), 1)


def save(name, tables):
    """Write each table to results/<name>/ as a CSV file."""
    folder = HERE / "results" / name
    for table_name, table in tables.items():
        table.to_csv(folder / f"{table_name}.csv")
    return folder


if __name__ == "__main__":
    check()
    path = sys.argv[1] if len(sys.argv) > 1 else "my_strategy.py"
    strategy = load_strategy(path)
    tables = evaluate(Path(path).stem, strategy)
    folder = save(Path(path).stem, tables)
    s, a = tables["summary"]["strategy"], tables["alphas"]
    print(f"{strategy.NAME}: average return {s['average return']:.1%} a year, "
          f"Sharpe ratio {s['Sharpe ratio']:.2f}, "
          f"worst drawdown {s['worst drawdown']:.0%}")
    for model, row in a.iterrows():
        print(f"  {model}: alpha {row['alpha']:.1%} a year, "
              f"t = {row['t']:.1f}")
    for side, row in tables["style"].iterrows():
        mix = row[STYLES].astype(float)
        print(f"  style of the {side} side: {mix.max():.0%} {mix.idxmax()}, "
              f"R-squared {row['R-squared']:.0%}")
    print(f"  tables in {folder.relative_to(HERE)}/")

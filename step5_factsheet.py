"""Step 5: make the factsheet. (Lecture 11)

It draws the growth chart, puts step 4's tables into factsheet.typ, and
writes results/<strategy>/factsheet.pdf: two pages laid out like a real
fund's sheet, labeled as a hypothetical backtest, and a page of notes.

    page 1   the strategy, its facts, the growth of $10,000 and the
             drawdowns beside the market's, and its returns over 1, 3, 5 and
             10 years and by calendar year, before and after trading costs
    page 2   risk, alphas and factor loadings, style boxes, industry
             weights, the largest holdings, and how it was all made
    page 3   notes on how each number is worked out, which a real fund's
             sheet would not print: the formulas, arithmetic or compound

make_factsheet() runs the parts in order; each has its own function below.
run.py calls steps 3 and 4, then this step. To run it on its own:

    uv run step5_factsheet.py examples/gross_profitability.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                    # draw to files, not to a window
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter
import numpy as np
import pandas as pd
import typst

from step3_backtest import COST, MICROCAP, load_strategy
from step4_evaluate import STYLES, load_factors

HERE = Path(__file__).parent
TEMPLATE = HERE / "factsheet.typ"
YEARS_SHOWN = 10          # calendar years in the table on page 1
TOP = 10                  # holdings listed on each side
INK, GREY = "#1d2b3a", "#a0a0a0"   # the strategy's colour and the market's


def num(x, decimals=1, scale=100):
    """A number as the factsheet prints it: 0.1234 -> '12.3', with a true
    minus sign, and a dash when it is missing."""
    if pd.isna(x):
        return "–"
    text = f"{scale * x:.{decimals}f}"
    if float(text) == 0:
        text = text.lstrip("-")          # no "-0.0"
    return text.replace("-", "−")


def month_name(month):
    """'2003-03' -> 'Mar 2003'."""
    return pd.Period(month, "M").strftime("%b %Y")


def noted(text, note):
    """A label that carries a note: the template prints the note's number
    after it, and the note itself on page 3 (see notes())."""
    return {"text": text, "note": note}


def growth(r, start=10_000):
    """What `start` dollars grow to, month by month, at the returns r."""
    return start * (1 + r).cumprod()


def whole_percents(weights):
    """Weights as whole percents that still add up to 100: round down, then
    round up the ones with the largest remainders."""
    raw = 100 * weights / weights.sum()
    out = np.floor(raw)
    short = int(round(100 - out.sum()))
    out[(raw - out).sort_values(ascending=False).index[:short]] += 1
    return out.astype(int)


def read_tables(name):
    """Step 3's returns and holdings and step 4's tables, for one strategy."""
    folder = HERE / "results" / name
    if not (folder / "periods.csv").exists():
        raise SystemExit(f"No tables for {name} yet: run step 4 first.")

    def read(table, **options):
        return pd.read_csv(folder / f"{table}.csv", **options)

    returns = read("returns")
    returns["month"] = pd.PeriodIndex(returns["month"], freq="M")
    return {"returns": returns.set_index("month"),
            "holdings": read("holdings"),
            "summary": read("summary", index_col=0),
            "alphas": read("alphas", index_col="model"),
            "style": read("style", index_col=0),
            "periods": read("periods", index_col=0),
            "calendar": read("calendar", index_col=0),
            "industries": read("industries", index_col="industry"),
            "top_holdings": read("top_holdings", index_col=0)}


def growth_chart(net, market, name, path):
    """Growth of $10,000 in the strategy, after costs, and in the market,
    on a log scale, so equal percentage gains look equal."""
    fig, ax = plt.subplots(figsize=(6.4, 2.7))
    when = net.index.to_timestamp(how="end")
    ax.plot(when, growth(net), color=INK, lw=1.6,
            label=f"{name}, after costs")
    ax.plot(when, growth(market), color=GREY, lw=1.2,
            label="US stock market")
    ax.set_yscale("log")
    top = max(growth(net).max(), growth(market).max())
    subs = (1, 2, 5) if top < 1_000 * 10_000 else (1,)   # fewer labels on a long range
    ax.yaxis.set_major_locator(LogLocator(subs=subs))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e6e6e6", lw=0.6)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, transparent=True)
    plt.close(fig)


def drawdown(r):
    """How far the value stands below its highest point so far, month by
    month: the same two lines as summary() in step 4."""
    wealth = (1 + r).cumprod()
    return wealth / wealth.cummax() - 1


def drawdown_chart(net, market, path):
    """The strategy's drawdowns, after costs, shaded, and the market's."""
    fig, ax = plt.subplots(figsize=(6.4, 1.6))
    when = net.index.to_timestamp(how="end")
    ax.fill_between(when, 100 * drawdown(net), 0, color=INK, alpha=0.75,
                    lw=0, label="Strategy, after costs")
    ax.plot(when, 100 * drawdown(market), color=GREY, lw=1.0,
            label="US stock market")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e6e6e6", lw=0.6)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 0.98),
              ncols=2)                   # above the plot, clear of the data
    fig.tight_layout()
    fig.savefig(path, transparent=True)
    plt.close(fig)


def facts(strategy, tables):
    """The facts sidebar: how the strategy is built, in a few lines."""
    returns, holdings = tables["returns"], tables["holdings"]
    last = holdings[holdings["month"] == holdings["month"].max()]
    n_long = int((last["group"] == strategy.GROUPS).sum())
    held = f"{n_long} stocks"
    if strategy.LONG_SHORT:
        n_short = int((last["group"] == 1).sum())
        held = f"{n_long} long, {n_short} short"
    if strategy.GROUPS == 1:
        groups = "1: every stock with a signal"
    else:
        groups = f"{strategy.GROUPS}, sorted on the signal"
    return [
        ["Type", "Long-short" if strategy.LONG_SHORT else "Long-only"],
        ["Holds", "the top group, and shorts the bottom group"
         if strategy.LONG_SHORT else "the top group"],
        ["Groups", groups],
        ["Weights", "by market cap" if strategy.WEIGHTS == "value" else "equal"],
        ["Rebalanced", "monthly"],
        ["Stocks", f"US common stocks above the {MICROCAP:.0%} NYSE size "
                   "cutoff"],
        ["Trading cost", f"{100 * COST:.1f}% of each dollar traded"],
        [noted("Turnover", "turnover"),
         f"{returns['turnover'].mean():.0%} a month on average, "
         "bought plus sold"],
        ["Holdings", f"{held} ({month_name(last['month'].iloc[0])})"],
        [noted("Benchmark", "market"),
         "the US stock market, weighted by market cap"],
        ["Period", f"{month_name(returns.index[0])} to "
                   f"{month_name(returns.index[-1])}"],
    ]


def return_tables(tables):
    """Page 1's two tables: returns over periods and by calendar year."""
    labels = {"before costs": "Before costs", "after costs": "After costs",
              "market": "US stock market"}
    periods = tables["periods"]
    calendar = tables["calendar"].tail(YEARS_SHOWN)
    return (
        {"header": ["", "1 year", "3 years", "5 years", "10 years",
                    "Since start"],
         "rows": [[labels[row]] + [num(v) for v in periods.loc[row]]
                  for row in labels]},
        {"header": [""] + [str(year) for year in calendar.index],
         "rows": [[labels[col]] + [num(v) for v in calendar[col]]
                  for col in labels]},
    )


def risk_table(tables):
    """Risk and risk-adjusted return, the strategy beside the market."""
    s = tables["summary"]
    beta = tables["alphas"].loc["CAPM", "mktrf"]

    def row(label, metric, note, decimals=1, scale=100):
        return [noted(label, note)] + [
            num(float(s.loc[metric, col]), decimals, scale)
            for col in ("strategy", "market")]

    return {"header": ["", "Strategy", "Market"],
            "rows": [row("Average return, % a year", "average return",
                         "average"),
                     row("Volatility, % a year", "volatility", "volatility"),
                     row("Sharpe ratio", "Sharpe ratio", "sharpe", 2, 1),
                     row("Worst drawdown, %", "worst drawdown", "drawdown"),
                     ["Its peak", month_name(s.loc["drawdown from", "strategy"]),
                      month_name(s.loc["drawdown from", "market"])],
                     ["Its trough", month_name(s.loc["drawdown to", "strategy"]),
                      month_name(s.loc["drawdown to", "market"])],
                     [noted("Beta", "alpha"), num(beta, 2, 1), "1.00"]]}


def alpha_table(tables):
    """Each model's alpha, its t-statistic, and the factor loadings."""
    a = tables["alphas"]
    factors = ["mktrf", "smb", "hml", "rmw", "cma", "umd"]
    rows = []
    for model, r in a.iterrows():
        loadings = ["" if pd.isna(r[f]) else num(r[f], 2, 1) for f in factors]
        rows.append([model, num(r["alpha"]), num(r["t"], 1, 1)] + loadings)
    return {"header": ["Model", "Alpha, % a year", "t-statistic",
                       "Mkt-RF", "SMB", "HML", "RMW", "CMA", "UMD"],
            "rows": rows}


def style_boxes(strategy, tables):
    """One style box per side: the weights on the six style portfolios and
    T-bills, in whole percents, with the R-squared."""
    boxes = []
    for side, r in tables["style"].iterrows():
        pct = whole_percents(r[STYLES].astype(float).clip(lower=0))
        title = {"long": "Long side", "short": "Short side"}[side]
        if not strategy.LONG_SHORT:
            title = "Holdings"
        boxes.append({"title": title,
                      "cells": [int(pct[s]) for s in STYLES[:6]],
                      "tbills": int(pct["T-bills"]),
                      "rsq": num(r["R-squared"], 0),
                      "intercept": num(r["intercept"])})
    return boxes


def industry_table(strategy, tables):
    """Each side's weight in each industry beside the market's, in %."""
    t = tables["industries"]
    if strategy.LONG_SHORT:
        t = t.assign(net=t["long"] - t["short"])
        cols, header = ["long", "short", "net", "market"], ["Long", "Short",
                                                            "Net", "Market"]
    else:
        cols, header = ["long", "market"], ["Holdings", "Market"]
    return {"header": ["Industry"] + header,
            "rows": [[industry] + [num(r[c]) for c in cols]
                     for industry, r in t.iterrows()]}


def holdings_tables(strategy, tables):
    """The largest positions on each side at the last rebalance."""
    top = tables["top_holdings"]
    out = []
    for side, rows in top.groupby("side", sort=False):
        title = {"long": "Long", "short": "Short"}[side]
        if not strategy.LONG_SHORT:
            title = "Holdings"
        out.append({"title": title,
                    "rows": [[r["ticker"] if pd.notna(r["ticker"]) else "–",
                              str(r["name"]).title()[:28]
                              if pd.notna(r["name"]) else "–",
                              num(r["weight"])]
                             for _, r in rows.head(TOP).iterrows()]})
    return out


def method(strategy):
    """How the numbers were made, and what they cannot show."""
    holds = ("holds the top group and shorts the bottom one"
             if strategy.LONG_SHORT else "holds the top group")
    weights = ("by market cap" if strategy.WEIGHTS == "value"
               else "equally")
    text = [
        "This is a hypothetical backtest: the strategy's rule applied to past "
        "data. No money was invested, and no investor earned these returns.",
        f"At the end of each month the code computes the signal for every US "
        f"common stock, leaves out stocks below the {MICROCAP:.0%} NYSE size "
        f"cutoff, sorts the rest into {strategy.GROUPS} "
        f"group{'s' if strategy.GROUPS > 1 else ''} with NYSE breakpoints, "
        f"and {holds}, weighted {weights}, for the next month.",
        f"Returns after costs subtract a trading cost of {100 * COST:.1f}% "
        f"of each dollar bought or sold; returns before costs do not. "
        f"Neither deducts management fees or taxes"
        f"{', or the cost of borrowing the stocks sold short' if strategy.LONG_SHORT else ''}.",
    ]
    if strategy.LONG_SHORT:
        text.append("A long-short strategy puts no money down: its return "
                    "is the long side's minus the short side's, and it "
                    "earns no interest on cash.")
    text += [
        "The notes below say how each number is worked out.",
        "Data: CRSP and Compustat through WRDS; the factors, the style "
        "portfolios and the market from the Ken French Data Library.",
        "Limitations: the code cannot check whether a signal uses "
        "information investors did not have at the time; a strategy chosen "
        "after trying many can look good by chance; trading costs at scale "
        "may be higher than assumed; and past returns, real or simulated, "
        "do not predict future returns.",
    ]
    return " ".join(text)


# The notes, in the order their numbers first appear on the sheet. A label
# made with noted(text, key) prints the number of the note with that key.
NOTES = ["turnover", "market", "growth", "drawdown", "returns", "calendar",
         "average", "volatility", "sharpe", "alpha", "style", "industries"]


def notes(strategy, tables):
    """How each number on the sheet is worked out, one note per key in
    NOTES. The text is Typst markup: $...$ is math, \\$ a dollar sign."""
    n = {key: i + 1 for i, key in enumerate(NOTES)}
    ls = strategy.LONG_SHORT
    returns = tables["returns"]
    rebalanced = month_name(tables["holdings"]["month"].max())
    held = month_name(returns.index[-1])

    # a calendar year on page 1 that the backtest covers only in part
    partial = ""
    shown = tables["calendar"].tail(YEARS_SHOWN).index
    for year in shown:
        months = returns.index[returns.index.year == year]
        if len(months) < 12:
            partial += (f" {year} covers {months[0].strftime('%B')} to "
                        f"{months[-1].strftime('%B')} only.")

    text = {
        "turnover": (
            "*Turnover.* At each rebalance, "
            "$sum_i abs(w_i^\"new\" - w_i^\"drift\")$, where "
            "$w_i^\"drift\"$ is stock $i$'s weight after a month of moving "
            "with its return, and a stock bought or sold in full counts its "
            "whole weight; replacing the whole portfolio is 200%. "
            + ("The long and short sides' turnovers are added. " if ls else "")
            + "The figure is the arithmetic average over all months. Each "
            f"month's trading cost, {100 * COST:.1f}% times that month's "
            "turnover, comes off that month's return."),
        "market": (
            "*US stock market.* Ken French's market return, Mkt-RF plus the "
            "T-bill rate: every US common stock on the NYSE, AMEX and Nasdaq, "
            "weighted by market cap, microcaps included. It is the Market "
            "column everywhere except the industry weights "
            f"(note {n['industries']})."),
        "growth": (
            "*Growth of \\$10,000.* \\$10,000 × "
            "$(1+r_1)(1+r_2) dots.c (1+r_t)$, compounding the monthly returns "
            "after costs, on a log scale, where equal percentage changes are "
            "equal steps."
            + (" A long-short strategy puts no money down: the line is "
               "\\$10,000 earning the long side's return minus the short "
               "side's each month, with no interest on the cash." if ls
               else "")),
        "drawdown": (
            "*Drawdowns.* Each month-end value divided by the highest "
            "month-end value so far, minus 1, after costs; a fall and "
            "recovery within a month does not show. The worst drawdown is "
            "the lowest of these; its peak is the month of the highest value "
            "before it, its trough the month it was reached."),
        "returns": (
            "*Returns, % a year.* Compound (geometric) averages: over the "
            "last $N$ months, $[(1+r_1)(1+r_2) dots.c (1+r_N)]^(12\\/N) - 1$, "
            "the steady yearly return that would have grown the money as "
            "much. _Since start_ uses every month. These are not the "
            f"arithmetic average return on page 2 (note {n['average']})."),
        "calendar": (
            "*Calendar-year returns.* Each year's monthly returns "
            "compounded: "
            "$(1+r_\"Jan\")(1+r_\"Feb\") dots.c (1+r_\"Dec\") - 1$." + partial),
        "average": (
            "*Average return.* The arithmetic mean of the monthly returns "
            "after costs, times 12: $12 × (r_1 + r_2 + dots.c + r_T)\\/T$ "
            "over all $T$ months. It is not compounded, so it differs from "
            f"the _Since start_ return on page 1 (note {n['returns']}), which "
            "is; with volatile returns the compound return is the lower."),
        "volatility": (
            "*Volatility.* The standard deviation of the monthly returns "
            "after costs, times $sqrt(12)$: the sample standard deviation, "
            "dividing by $T - 1$."),
        "sharpe": (
            "*Sharpe ratio.* The average monthly excess return divided by its "
            "standard deviation, times $sqrt(12)$. "
            + ("The strategy's excess return is its return after costs: a "
               "long-short strategy puts no money down, so its return is "
               "already an excess return. " if ls else
               "The excess return is the return after costs minus that "
               "month's T-bill rate. ")
            + "The market's is Mkt-RF."),
        "alpha": (
            "*Alpha, loadings and beta.* Each model is an ordinary "
            "least-squares regression of the monthly excess return after "
            f"costs (note {n['sharpe']}) on the factors' monthly returns, "
            "over every month. Alpha is the intercept times 12, not "
            "compounded. The t-statistic is the intercept divided by its "
            "standard error, with no correction for heteroskedasticity or "
            "autocorrelation; beyond about ±2, an alpha this large would be "
            "unlikely if the true alpha were zero. The loadings are the "
            "slopes; beta is the CAPM's Mkt-RF loading. The factors, from "
            "Ken French: Mkt-RF, the market minus T-bills; SMB, small minus "
            "big stocks; HML, high minus low book-to-market; RMW, robust "
            "minus weak profitability; CMA, conservative minus aggressive "
            "investment; UMD, past winners minus past losers (momentum)."),
        "style": (
            "*Style boxes.* Sharpe's style analysis of "
            + ("each side's" if ls else "the holdings'")
            + " monthly returns before costs: the weights on Ken French's six "
            "portfolios by size and P/E (each weighted by market cap) and on "
            "T-bills, each zero or more and adding to 100%, that make the "
            "variance of the return minus the mix's return as small as "
            "possible. R² is 1 minus that variance divided by the variance "
            "of the return; the intercept is the average monthly difference "
            "times 12. The weights are shown in whole percents."),
        "industries": (
            "*Industry weights and largest holdings.* At the last rebalance, "
            f"the end of {rebalanced}, for the returns of {held}: each "
            "stock's share of its side's value. The industries are Ken "
            "French's twelve, from each stock's SIC code at the time. The "
            "Market column weights every US common stock in the data, "
            "microcaps included, by market cap"
            + ("; Net is long minus short." if ls else ".")),
    }
    return [{"key": key, "text": text[key]} for key in NOTES]


def fill(name, strategy, tables):
    """Everything the template prints, as text, in one dictionary."""
    returns = tables["returns"]
    periods, calendar = return_tables(tables)
    return {
        "name": strategy.NAME,
        "subtitle": (f"US stocks, monthly, {month_name(returns.index[0])} to "
                     f"{month_name(returns.index[-1])}. Benchmark: the US "
                     "stock market."),
        "objective": strategy.OBJECTIVE,
        "description": strategy.DESCRIPTION,
        "facts": facts(strategy, tables),
        "growth": f"/results/{name}/growth.svg",
        "drawdowns": f"/results/{name}/drawdowns.svg",
        "periods": periods,
        "calendar": calendar,
        "risk": risk_table(tables),
        "alphas": alpha_table(tables),
        "style": style_boxes(strategy, tables),
        "industries": industry_table(strategy, tables),
        "holdings": holdings_tables(strategy, tables),
        "method": method(strategy),
        "notes": notes(strategy, tables),
        # The course's not-investment-advice sentence, word for word as in
        # every other course document.
        "footer": ("Hypothetical backtest made with the FNCE 3030 course code. "
                   "These materials are for teaching only and are not "
                   "investment advice."),
    }


def make_factsheet(name, strategy):
    """The parts above, in order: the chart, the text, the PDF."""
    tables = read_tables(name)
    folder = HERE / "results" / name
    factors = load_factors()
    # the months step 4 measured: those with factor returns
    returns = tables["returns"]
    tables["returns"] = returns[returns.index.isin(factors.index)]
    net = tables["returns"]["net"]
    market = (factors["mktrf"] + factors["rf"]).loc[net.index]
    # [slide: compile]
    growth_chart(net, market, strategy.NAME, folder / "growth.svg")
    drawdown_chart(net, market, folder / "drawdowns.svg")
    data = fill(name, strategy, tables)
    (folder / "factsheet.json").write_text(
        json.dumps(data, indent=1, ensure_ascii=False))
    pdf = folder / "factsheet.pdf"
    typst.compile(str(TEMPLATE), output=str(pdf), root=str(HERE),
                  sys_inputs={"data": f"/results/{name}/factsheet.json"})
    return pdf
    # [end]


def check():
    """Check the numbers this step works out, on made-up values."""
    assert num(0.1234) == "12.3" and num(-0.05) == "−5.0"
    assert num(-0.0004) == "0.0" and num(np.nan) == "–"
    assert num(1.234, 2, 1) == "1.23"
    # $10,000 that gains 10% and then loses half is $11,000, then $5,500
    assert np.allclose(growth(pd.Series([0.1, -0.5])), [11_000, 5_500])
    # thirds round to 33, 33 and 34, so the box still adds up to 100
    thirds = whole_percents(pd.Series([0.333, 0.333, 0.334]))
    assert list(thirds) == [33, 33, 34]
    assert month_name("2003-03") == "Mar 2003"
    # up 10%, down half, up 20%: 10% below the peak after the rise
    assert np.allclose(drawdown(pd.Series([0.1, -0.5, 0.2])), [0, -0.5, -0.4])


if __name__ == "__main__":
    check()
    path = sys.argv[1] if len(sys.argv) > 1 else "my_strategy.py"
    strategy = load_strategy(path)
    pdf = make_factsheet(Path(path).stem, strategy)
    print(f"{strategy.NAME}: factsheet in {pdf.relative_to(HERE)}")

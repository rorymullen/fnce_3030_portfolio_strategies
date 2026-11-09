"""Step 2: build one monthly table of stocks. Run it once, after step 1.

    uv run step2_prepare.py

It joins the CRSP and Compustat files into data/stocks.parquet: one row per
stock per month, with the columns DATA.md describes. Two rules keep it honest:

    no look-ahead     a firm's annual accounting numbers count only from six
                      months after its fiscal year ends, once they were public
    no survivorship   stocks that later disappeared stay in, with their final
                      returns; leaving them out would flatter every strategy

Nothing here needs WRDS, so you can rerun this step at any time.

prepare() runs the parts in order; each has its own function below:

    load_crsp()       the monthly stock file: returns, market caps, names,
                      exchanges and industries
    sic_at_the_time() each stock-month's industry code as recorded then
    book_equity()     book equity, the Fama-French way
    load_accounts()   the annual accounts, linked to CRSP's stocks, with the
                      month each report became public
    add_accounts()    each stock-month's latest public report
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DATA = HERE / "data"
LAG = 6                 # months after a fiscal year ends before its numbers count
STALE = 12              # months after which a report is too old to use

EXCHANGES = {"N": "NYSE", "A": "AMEX", "Q": "NASDAQ"}

# Ken French's twelve industries, by SIC code (his Siccodes12 file), with
# readable names. A code in none of these ranges is "Other".
INDUSTRIES = {
    "Nondurables": [(100, 999), (2000, 2399), (2700, 2749), (2770, 2799),
                    (3100, 3199), (3940, 3989)],
    "Durables": [(2500, 2519), (2590, 2599), (3630, 3659), (3710, 3711),
                 (3714, 3714), (3716, 3716), (3750, 3751), (3792, 3792),
                 (3900, 3939), (3990, 3999)],
    "Manufacturing": [(2520, 2589), (2600, 2699), (2750, 2769), (3000, 3099),
                      (3200, 3569), (3580, 3629), (3700, 3709), (3712, 3713),
                      (3715, 3715), (3717, 3749), (3752, 3791), (3793, 3799),
                      (3830, 3839), (3860, 3899)],
    "Energy": [(1200, 1399), (2900, 2999)],
    "Chemicals": [(2800, 2829), (2840, 2899)],
    "Business Equipment": [(3570, 3579), (3660, 3692), (3694, 3699),
                           (3810, 3829), (7370, 7379)],
    "Telecom": [(4800, 4899)],
    "Utilities": [(4900, 4949)],
    "Shops": [(5000, 5999), (7200, 7299), (7600, 7699)],
    "Health": [(2830, 2839), (3693, 3693), (3840, 3859), (8000, 8099)],
    "Finance": [(6000, 6999)],
}

ACCOUNTS = ["sales", "cost_of_goods_sold", "assets", "book_equity", "earnings"]


def number(column):
    """A column as plain floating-point numbers, missing values as NaN."""
    return pd.to_numeric(column, errors="coerce").astype("float64")


def industry(sic):
    """French's twelve industries from SIC codes."""
    sic = number(sic)
    names = pd.Series("Other", index=sic.index)
    for name, ranges in INDUSTRIES.items():
        for low, high in ranges:
            names[(sic >= low) & (sic <= high)] = name
    return names


def sic_at_the_time(months, history):
    """Each stock-month's SIC code as CRSP recorded it at the time. A firm
    can change industry, and classing its past by today's code would look
    ahead. `months` has permno and month; `history` has permno, the code, and
    the dates it held. A month the history does not cover gets no code."""
    left = months[["permno", "month"]].assign(
        t=months["month"].apply(lambda p: p.ordinal), row=range(len(months)))
    h = history.assign(
        permno=history["permno"].astype("int64"),
        t=pd.to_datetime(history["secinfostartdt"]).dt.to_period("M")
        .apply(lambda p: p.ordinal),
        end=pd.to_datetime(history["secinfoenddt"]).dt.to_period("M")
        .apply(lambda p: p.ordinal),
        sic=number(history["siccd"]))
    found = pd.merge_asof(left.sort_values("t"),
                          h[["permno", "t", "end", "sic"]].sort_values("t"),
                          on="t", by="permno", direction="backward")
    found.loc[found["t"] > found["end"], "sic"] = np.nan   # past its end date
    return found.set_index("row")["sic"].sort_index().set_axis(months.index)


def load_crsp(path=None, history_path=None):
    """The monthly stock file, one row per stock per month. CRSP gives market
    cap in thousands of dollars; this table keeps it in millions. The return
    already includes a delisted stock's final return. The industry comes from
    the SIC code at the time, or today's code where CRSP's history has a gap."""
    crsp = pd.read_parquet(path or DATA / "crsp_monthly.parquet")
    history = pd.read_parquet(history_path or DATA / "crsp_sic_history.parquet")
    stocks = pd.DataFrame({
        "permno": crsp["permno"].astype("int64"),
        "month": pd.to_datetime(crsp["mthcaldt"]).dt.to_period("M"),
        "ticker": crsp["ticker"].astype("string"),
        "name": crsp["issuernm"].astype("string"),
        "exchange": crsp["primaryexch"].map(EXCHANGES),
        "ret": number(crsp["mthret"]),
        "market_cap": number(crsp["mthcap"]) / 1e3,   # thousands -> millions
    })
    if stocks.duplicated(["permno", "month"]).any():
        raise SystemExit("CRSP has two rows for one stock in one month: "
                         "tell your instructor.")
    sic = sic_at_the_time(stocks, history).fillna(number(crsp["siccd"]))
    stocks.insert(5, "industry", industry(sic))
    return stocks


def book_equity(a):
    """Book equity, as Fama and French measure it: shareholders' equity, plus
    deferred taxes, minus preferred stock. Each part falls back on the next
    best item when Compustat leaves it blank."""
    equity = a["seq"].fillna(a["ceq"] + a["pstk"]).fillna(a["at"] - a["lt"])
    preferred = a["pstkrv"].fillna(a["pstkl"]).fillna(a["pstk"]).fillna(0)
    return equity + a["txditc"].fillna(0) - preferred


def load_accounts(comp_path=None, link_path=None):
    """The annual accounts, linked to CRSP's permnos, each with the month it
    became public: LAG months after the fiscal year ended."""
    comp = pd.read_parquet(comp_path or DATA / "compustat_annual.parquet")
    link = pd.read_parquet(link_path or DATA / "ccm_link.parquet")
    items = ["sale", "cogs", "at", "lt", "seq", "ceq", "pstk", "pstkrv",
             "pstkl", "txditc", "ib"]
    comp[items] = comp[items].apply(number)
    comp["datadate"] = pd.to_datetime(comp["datadate"])
    comp = comp.drop_duplicates(["gvkey", "datadate"], keep="last")
    # [slide: accounts]
    accounts = pd.DataFrame({
        "gvkey": comp["gvkey"], "datadate": comp["datadate"],
        "sales": comp["sale"], "cost_of_goods_sold": comp["cogs"],
        "assets": comp["at"], "book_equity": book_equity(comp),
        "earnings": comp["ib"],
        "available": comp["datadate"].dt.to_period("M") + LAG,
    })
    # [end]
    # keep each report only while its link to a CRSP stock was in force
    link = link.assign(permno=link["permno"].astype("int64"),
                       linkdt=pd.to_datetime(link["linkdt"]),
                       linkenddt=pd.to_datetime(link["linkenddt"])
                       .fillna(pd.Timestamp("2099-12-31")))
    linked = accounts.merge(link, on="gvkey")
    linked = linked[(linked["datadate"] >= linked["linkdt"])
                    & (linked["datadate"] <= linked["linkenddt"])]
    linked = linked.sort_values("datadate").drop_duplicates(
        ["permno", "available"], keep="last")
    return linked[["permno", "available"] + ACCOUNTS]


def add_accounts(stocks, accounts):
    """Give each stock-month the latest report that was already public, but
    none older than STALE months: no look-ahead, and no stale numbers."""
    left = stocks.assign(t=stocks["month"].apply(lambda p: p.ordinal))
    right = accounts.assign(t=accounts["available"].apply(lambda p: p.ordinal))
    panel = pd.merge_asof(left.sort_values("t"),
                          right.drop(columns="available").sort_values("t"),
                          on="t", by="permno", direction="backward",
                          tolerance=STALE - 1)
    return (panel.drop(columns="t").sort_values(["permno", "month"])
            .reset_index(drop=True))


def prepare():
    """The parts above, in order: the monthly table, saved."""
    for f in ["crsp_monthly.parquet", "compustat_annual.parquet",
              "ccm_link.parquet", "crsp_sic_history.parquet"]:
        if not (DATA / f).exists():
            raise SystemExit(f"No data/{f} yet: run step 1 first.")
    print("Step 2: building the monthly table of stocks...")
    stocks = add_accounts(load_crsp(), load_accounts())
    biggest = stocks.loc[stocks["month"] == stocks["month"].max(),
                         "market_cap"].max()
    if not 1e5 <= biggest <= 1e8:        # $100 billion to $100 trillion
        raise SystemExit(f"The largest market cap is {biggest:,.0f} million "
                         "dollars, which cannot be right: tell your instructor.")
    stocks.to_parquet(DATA / "stocks.parquet")
    return stocks


def check():
    """Check the rules above on made-up firms, worked by hand."""
    # book equity: 100 of equity + 10 of deferred taxes - 5 of preferred = 105;
    # with no seq, ceq + pstk stands in (50 + 20 = 70, minus 20 preferred)
    a = pd.DataFrame({"seq": [100, np.nan], "ceq": [90, 50], "pstk": [5, 20],
                      "at": [300, 200], "lt": [200, 100], "pstkrv": [5, np.nan],
                      "pstkl": [np.nan, np.nan], "txditc": [10, np.nan]},
                     dtype=float)
    assert np.allclose(book_equity(a), [105, 50])
    # industries
    assert list(industry(pd.Series([7372, 6020, 9999, np.nan]))) == [
        "Business Equipment", "Finance", "Other", "Other"]
    # the code at the time: a firm making hardware (3570) through June 2010
    # and software (7372) from July 2010; stock 2 has no history at all; stock
    # 3's history stops at the end of 2005
    history = pd.DataFrame({"permno": [1, 1, 3],
                            "secinfostartdt": ["1990-01-01", "2010-07-01",
                                               "1990-01-01"],
                            "secinfoenddt": ["2010-06-30", "2099-12-31",
                                             "2005-12-31"],
                            "siccd": [3570, 7372, 6020]})
    months = pd.DataFrame({"permno": [1, 1, 1, 2, 3, 3], "month": pd.PeriodIndex(
        ["2010-06", "2010-07", "1989-12", "2010-06", "2005-12", "2008-01"],
        freq="M")})
    sic = sic_at_the_time(months, history)
    assert sic.iloc[0] == 3570 and sic.iloc[1] == 7372 and sic.iloc[4] == 6020
    assert sic.iloc[2:4].isna().all() and np.isnan(sic.iloc[5])   # not covered
    # the lag: a December 2000 report counts from June 2001, through May 2002
    months = pd.period_range("2001-04", "2002-07", freq="M")
    stocks = pd.DataFrame({"permno": 1, "month": months})
    report = pd.DataFrame({"permno": [1], "available":
                           [pd.Period("2000-12", "M") + LAG],
                           **{c: [1.0] for c in ACCOUNTS}})
    panel = add_accounts(stocks, report).set_index("month")
    assert panel.loc["2001-05", "sales"] != panel.loc["2001-05", "sales"]  # NaN
    assert panel.loc["2001-06", "sales"] == 1 and panel.loc["2002-05", "sales"] == 1
    assert np.isnan(panel.loc["2002-06", "sales"])                       # stale


if __name__ == "__main__":
    check()
    stocks = prepare()
    print(f"  {len(stocks):,} stock-months, {stocks['permno'].nunique():,} "
          f"stocks, {stocks['month'].min()} to {stocks['month'].max()}")
    print("Saved data/stocks.parquet. Next: uv run run.py "
          "examples/gross_profitability.py")

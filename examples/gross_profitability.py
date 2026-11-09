"""Example: gross profitability (Novy-Marx, 2013).

Firms with high gross profits relative to their assets have earned higher
returns than firms with low ones. Gross profit is sales minus the cost of goods
sold. Novy-Marx argues it is the cleanest accounting measure of profitability,
because it comes before expenses that are really investments, such as
advertising and research and development.

As in the original study, financial firms are left out and stocks are sorted
into five value-weighted groups.

    uv run run.py examples/gross_profitability.py
"""

NAME = "Gross Profitability"
OBJECTIVE = ("Seeks to earn the gap in returns between the most and the least "
             "profitable US firms, with little exposure to the stock market "
             "as a whole.")
DESCRIPTION = (
    "Each month the strategy ranks US stocks by gross profitability: sales "
    "minus the cost of goods sold, divided by total assets, from annual "
    "accounts at least six months old, so that investors had seen them. It "
    "sorts the stocks into five groups on that ranking, buys the top group "
    "and shorts the bottom one, each side weighted by market cap. Gross profit "
    "sits near the top of the income statement, before spending such as "
    "research and advertising that builds future business, so it measures a "
    "firm's underlying profitability more cleanly than earnings do. Robert "
    "Novy-Marx (2013) found that profitable firms earned higher returns than "
    "unprofitable ones, even though they tend to be growth stocks, priced "
    "high relative to their book value. Financial firms are left out, as in "
    "that study, because their accounts are not comparable with other firms'.")

LONG_SHORT = True
GROUPS = 5
WEIGHTS = "value"


def signal(stocks):
    """Gross profits over total assets, with financial firms left out."""
    gross_profit = stocks["sales"] - stocks["cost_of_goods_sold"]
    assets = stocks["assets"].where(stocks["assets"] > 0)   # none on record: no ratio
    gp_to_assets = gross_profit / assets
    return gp_to_assets.where(stocks["industry"] != "Finance")

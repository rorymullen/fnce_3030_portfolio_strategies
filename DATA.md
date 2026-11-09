# The data your signal can use

Your `signal(stocks)` receives one table, the one step 2 saves as
`data/stocks.parquet`. It has one row per stock per month, from January 1963
to the latest month in your download: every ordinary common share of a US
company listed on the NYSE, AMEX or NASDAQ, including the stocks that later
disappeared.

A row describes its stock **at the end of its month**, month *t*. Everything
in it was known by then, so your signal may use any column of the row. The
code pairs your signal with the stock's return over the *next* month, *t*+1,
so you never shift returns yourself.

## The columns

| Column | What it is | Units |
|---|---|---|
| `permno` | CRSP's permanent number for the stock. It never changes, even when the ticker or the name does, so use it to follow a stock over time. | |
| `month` | The calendar month, *t*. | a pandas `Period` |
| `ticker` | The ticker symbol in that month. Tickers change and are reused: Facebook's FB became META in June 2022. Blank for a few rows. | |
| `name` | The company's name in that month, as CRSP records it. | |
| `exchange` | Where the stock was listed in that month: `NYSE`, `AMEX` or `NASDAQ`. | |
| `industry` | One of Ken French's twelve industries, from the industry (SIC) code CRSP recorded at the time: Nondurables, Durables, Manufacturing, Energy, Chemicals, Business Equipment, Telecom, Utilities, Shops, Health, Finance, Other. | |
| `ret` | The return over month *t*: the change in price plus any dividend, as a fraction of the price at the start of the month. If the stock stopped trading, it includes its final return. | a decimal: 0.05 is 5% |
| `market_cap` | Price times shares outstanding at the end of month *t*. | millions of dollars |
| `sales` | Net sales (revenue) for the fiscal year. | millions of dollars |
| `cost_of_goods_sold` | The cost of the goods or services sold that year. | millions of dollars |
| `assets` | Total assets at the end of the fiscal year. | millions of dollars |
| `book_equity` | Book value of the common equity, as Fama and French measure it: shareholders' equity, plus deferred taxes, minus preferred stock. It can be negative. | millions of dollars |
| `earnings` | Income before extraordinary items for the fiscal year. | millions of dollars |

## When the accounting numbers were known

The last five columns come from the firm's annual report in Compustat. A
firm publishes its report some weeks after its fiscal year ends, so a row
carries a report only from the **sixth month after the fiscal year ended**:
a report for a year ending in December 2000 appears in the rows for June 2001
onward. It stays until the next report replaces it, or for twelve months at
most, after which the columns are blank. They are also blank when Compustat
has no report for the firm, which is the case for about one row in six.

Your signal should return NaN (missing) for a stock whose columns are blank,
and NaN leaves the stock out that month. A division by zero gives an
infinite value, which the code refuses: turn a zero denominator into NaN
first, as `examples/gross_profitability.py` does with assets.

## Using earlier months

A signal may use a stock's earlier months as well as the current one. Rows
are in month order within each stock, so

    stocks.groupby("permno")["market_cap"].shift(12)

gives each stock's market cap twelve rows earlier: twelve months, unless the
stock skipped a month. Never shift by a negative number, and never use a
number worked out over the whole table (a stock's average return over all
its months, say): both look into the future.

## The other files

Step 1 also saves the Fama-French factor returns (`data/factors.csv`) and
Ken French's six portfolios by size and P/E (`data/styles.csv`). Step 4
uses them to measure your strategy; your signal does not see them.

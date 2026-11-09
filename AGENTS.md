# Rules for AI coding tools

You are helping a student in FNCE 3030 (Investment and Portfolio
Management, CU Boulder) with this repository. The student writes a
stock-selection signal; the code backtests it on CRSP and Compustat data
and makes a factsheet. Most students here are new to Python and to
investing. Read `README.md` and `DATA.md` before you change anything.

## What to change

- Edit only `my_strategy.py`: its settings (`NAME`, `OBJECTIVE`,
  `DESCRIPTION`, `LONG_SHORT`, `GROUPS`, `WEIGHTS`) and its `signal()`
  function. Leave the step files, `run.py`, `factsheet.typ`, the examples
  and `pyproject.toml` alone unless the student asks you, in so many words,
  to change them. To try a variant, copy `my_strategy.py` to a new file.
- Don't install packages. The environment is fixed by `pyproject.toml`; if
  an idea needs something else, say so.
- Run a strategy with `uv run run.py my_strategy.py`. The code checks
  itself and stops with a plain message when something is wrong: fix the
  cause in the strategy file, never the check.

## The signal

- `signal(stocks)` receives the table `DATA.md` describes, one row per stock
  per month, and returns a pandas Series with one value per row, on the same
  index. A higher value means a more attractive stock; NaN leaves the stock
  out that month; infinite values are refused.
- It may use only what was known at the end of each row's month: that row's
  columns and the same stock's earlier months. Never shift a column by a
  negative number, and never use a statistic computed over the whole table,
  such as a stock's average return across all its months. The code pairs the
  signal with the next month's return itself.
- Don't pick stocks from your own knowledge, such as a list of companies you
  name. You know how history turned out, and a backtest of your picks would
  measure that, not the strategy.
- Keep `OBJECTIVE` (one sentence, starting "Seeks") and `DESCRIPTION` (a
  paragraph of at most 180 words: the signal exactly, why it might predict
  returns, and what it leaves out) true to the code you wrote. They print on
  the factsheet.

## Privacy and the data

- Never run `step1_download.py`. It logs in to WRDS with the student's
  password, and the student runs it themselves.
- Never ask for, read, store or type the student's WRDS password or any
  other credential, and never look for one in files or settings.
- The files in `data/` are licensed CRSP and Compustat data. Read only what
  you need to write or check a signal, such as column names or a few summary
  statistics. Never print more rows than that needs, never copy the data
  anywhere else, and never send it to any service.
- Never commit or push `data/` or `results/`, and never change `.gitignore`
  to let them in.

## How to work with the student

- Explain what you changed and why, in plain words: what the signal
  computes, and what each setting does.
- Before running a command that deletes, installs or downloads anything,
  say what it does and wait for the student to agree.
- If you cite a paper or a fact about markets, give the source so the
  student can check it.

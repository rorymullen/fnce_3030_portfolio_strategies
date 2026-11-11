# FNCE 3030: Portfolio Strategies

Test an investment strategy of your own the way researchers and fund
managers do. You write one function, a *signal* that ranks stocks each month.
The code backtests it on CRSP and Compustat, the same stock and accounting
data that finance researchers use, and turns the results into a factsheet
laid out like a real fund's, with a page of notes on how each number is
worked out.

This goes with Lectures 10 and 11 of FNCE 3030, Investment and Portfolio
Management, at CU Boulder. It is optional and for interest only: it earns no
credit, and nothing in the code is on an exam. What you get is a strategy you
built and tested yourself, and a factsheet modeled on real ones from
Dodge & Cox, MSCI and Diamond Hill.

## What you need

- A WRDS class account, for the data. The sign-up link and the class code
  are on Canvas.
- Two free tools: `uv`, which installs Python and everything the code uses,
  and `git`, which downloads the code and its updates.
  [SETUP.md](SETUP.md) shows how, on a Mac or on Windows.
- If you like, an AI tool to help you write your signal (see below).

## The five steps

| Step | File | What it does | Lecture |
|---|---|---|---|
| 1 | `step1_download.py` | Downloads CRSP, Compustat and the Fama-French factors. You run it once, yourself. | 10 |
| 2 | `step2_prepare.py` | Builds one monthly table of stocks, each with its firm's accounts from the time they were public. | 10 |
| 3 | `step3_backtest.py` | Sorts stocks on your signal each month, forms the portfolio, and works out its returns after trading costs. | 10 |
| 4 | `step4_evaluate.py` | Measures the results: returns, risk, alphas from three factor models, style, industries and holdings. | 11 |
| 5 | `step5_factsheet.py` | Makes the factsheet, `results/<strategy>/factsheet.pdf`. | 11 |

Steps 1 and 2 run once. After that, one command runs steps 3 to 5 for any
strategy:

    uv run run.py my_strategy.py

Each step first checks itself on a small made-up example, worked by hand,
and stops with a plain message if anything is wrong.

## Your file

`my_strategy.py` is the only file you need to change. It holds a few
settings (a name and a description for the factsheet; long-only or
long-short; how many groups to sort stocks into; value or equal weights) and
one function, `signal()`. Your signal gives each stock a number each month,
using only what was known at the end of that month, and a higher number means
a more attractive stock. [DATA.md](DATA.md) lists every column you can use.
The code does everything else.

## Two examples

`examples/` holds two finished strategies to learn from, one serious and one
silly:

- `gross_profitability.py` buys the most profitable firms and shorts the
  least profitable, following Novy-Marx (2013).
- `ai_picks.py`, the AI Picks Fund, holds fifty innovative companies an AI
  chatbot named. It has a deliberate flaw. Before Lecture 11, try to find it.

Run one to see a finished factsheet:

    uv run run.py examples/gross_profitability.py

## Using AI tools

AI tools are encouraged here: for ideas, for writing your signal, and for
explaining the code. ChatGPT Edu is free through CU: paste in `DATA.md` and
`my_strategy.py` and ask it for a signal. Claude Code or Codex can work in the
repository directly; they read [AGENTS.md](AGENTS.md), which gives them the
rules. The rules for you, from Lecture 10:

| Do | Don't |
|---|---|
| Type your WRDS password yourself | Paste it into a chat, or let an agent log in |
| Keep the data on your own computer | Upload it to a chatbot or to GitHub |
| Read an agent's commands first | Approve a delete or an install unread |
| Ask for sources, and look them up | Trust a cited paper until you find it |
| Ask an AI to explain code to you | Ask an AI to pick stocks: it knows the ending |

## The data stay with you

CRSP and Compustat are licensed: CU's subscription to WRDS lets you use them
for this course, not pass them on. They live in `data/` on your own computer:
never upload them to a chatbot, never share them, and never push them to
GitHub. Git already leaves `data/` and `results/` out of anything you commit.
Your factsheet shows only your strategy's results, and it is yours to share.

## Getting help

When something goes wrong, an AI tool is the quickest help. Tell it what
you ran, paste the whole message you saw, and ask what went wrong; Claude
Code or Codex can also read the files in the repository. Never paste your
password or rows of the data. Office hours are open as usual, but I can't
debug individual setups one on one.

---

Written for FNCE 3030 at the Leeds School of Business, University of Colorado
Boulder. Students in the course may use, change and run this code for their
own study, and what you make with it is yours. These materials are for
teaching only and are not investment advice. Prepared with AI assistance;
reviewed by the instructor, who bears responsibility for any remaining errors.

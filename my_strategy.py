"""Your strategy. This is the only file you need to change.

Fill in the settings, write your signal, then run:

    uv run run.py my_strategy.py

Your factsheet appears in results/my_strategy/factsheet.pdf. The two files in
examples/ are finished strategies to learn from.
"""

NAME = "My Strategy"     # the title of your factsheet
OBJECTIVE = ""           # one sentence for the factsheet, starting "Seeks"
DESCRIPTION = ""         # a paragraph for the factsheet, at most 180 words:
                         # the signal, exactly; why it might predict returns;
                         # and what is left out (the examples show how)

LONG_SHORT = True        # True: buy the top group and short the bottom group
                         # False: buy the top group only
GROUPS = 10              # groups to sort stocks into each month (10 = deciles)
WEIGHTS = "value"        # "value": by market cap; "equal": the same for each


# [slide: your file]
def signal(stocks):
    """One number per stock per month. Higher means more attractive.

    stocks has one row per stock per month; DATA.md lists its columns.
    Use only what was known at the end of that month.
    Return NaN for any stock you want to leave out.
    """
    raise SystemExit("No signal yet: write it here. examples/ has two.")
# [end]

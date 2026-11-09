"""Example: the AI Picks Fund.

We asked an AI chatbot to name fifty innovative US companies. This strategy
holds all of them, equally weighted.

This is a teaching example with a deliberate flaw. Before Lecture 11,
try to find it.

    uv run run.py examples/ai_picks.py

The chatbot was Claude (claude-opus-5-5), in a fresh session that knew
nothing about this course, on 1 November 2026. The prompt, word for word:

    List fifty innovative publicly traded US companies, with their stock
    tickers. Reply with exactly fifty lines, each in the form "TICKER,
    Company name", and nothing else.

Its answer is ANSWER below, unedited.
"""
import pandas as pd

NAME = "AI Picks Fund"
OBJECTIVE = ("Seeks long-term growth by holding innovative US companies "
             "chosen by an AI chatbot.")
DESCRIPTION = (
    "This is a teaching example with a deliberate flaw, explained in Lecture "
    "11: its results are not evidence that the strategy works. "
    "In November 2026 we asked an AI chatbot, Claude, to name fifty "
    "innovative publicly traded US companies, and we use its answer "
    "unedited. Each month the fund holds every company on that list whose "
    "stock is trading, equally weighted, so the number of holdings grows "
    "over time as the listed companies come to market. It needs no "
    "accounting data and no forecasts of its own: the chatbot's list is the "
    "whole of the selection process. Innovation is hard to measure from a "
    "firm's accounts, and a model trained on decades of writing about "
    "business can tell which companies have led their industries.")

LONG_SHORT = False
GROUPS = 1          # one group: hold every stock that has a signal
WEIGHTS = "equal"

ANSWER = """\
NVDA, NVIDIA Corporation
AAPL, Apple Inc.
MSFT, Microsoft Corporation
GOOGL, Alphabet Inc.
AMZN, Amazon.com, Inc.
META, Meta Platforms, Inc.
TSLA, Tesla, Inc.
AMD, Advanced Micro Devices, Inc.
AVGO, Broadcom Inc.
QCOM, Qualcomm Incorporated
AMAT, Applied Materials, Inc.
LRCX, Lam Research Corporation
KLAC, KLA Corporation
MU, Micron Technology, Inc.
ANET, Arista Networks, Inc.
SNPS, Synopsys, Inc.
ORCL, Oracle Corporation
CRM, Salesforce, Inc.
ADBE, Adobe Inc.
NOW, ServiceNow, Inc.
INTU, Intuit Inc.
WDAY, Workday, Inc.
PLTR, Palantir Technologies Inc.
SNOW, Snowflake Inc.
CRWD, CrowdStrike Holdings, Inc.
PANW, Palo Alto Networks, Inc.
ZS, Zscaler, Inc.
NET, Cloudflare, Inc.
DDOG, Datadog, Inc.
MDB, MongoDB, Inc.
HUBS, HubSpot, Inc.
TTD, The Trade Desk, Inc.
NFLX, Netflix, Inc.
UBER, Uber Technologies, Inc.
ABNB, Airbnb, Inc.
DASH, DoorDash, Inc.
XYZ, Block, Inc.
PYPL, PayPal Holdings, Inc.
COIN, Coinbase Global, Inc.
ISRG, Intuitive Surgical, Inc.
MRNA, Moderna, Inc.
VRTX, Vertex Pharmaceuticals Incorporated
REGN, Regeneron Pharmaceuticals, Inc.
LLY, Eli Lilly and Company
ILMN, Illumina, Inc.
DXCM, DexCom, Inc.
AXON, Axon Enterprise, Inc.
RKLB, Rocket Lab USA, Inc.
FSLR, First Solar, Inc.
DE, Deere & Company
"""

TICKERS = [line.split(",")[0] for line in ANSWER.splitlines()]


def signal(stocks):
    """1 for the fifty companies; NaN, which leaves a stock out, for the rest.

    Each company is found by the ticker it trades under in the last month of
    the data, and then held in every month it has a return."""
    last = stocks[stocks["month"] == stocks["month"].max()]
    chosen = last.loc[last["ticker"].isin(TICKERS), "permno"]
    picked = stocks["permno"].isin(chosen)
    return pd.Series(1.0, index=stocks.index).where(picked)

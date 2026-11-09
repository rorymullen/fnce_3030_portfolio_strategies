"""Step 1: download the data from WRDS. Run it once, yourself.

    uv run step1_download.py

It asks for your WRDS username and password, and WRDS sends a Duo push to your
phone. Then it saves what the later steps need in data/:

    CRSP          monthly stock returns and market caps, with each firm's
                  ticker, name and exchange, and its industry code over time
    Compustat     annual accounting data: sales, costs, assets, book equity,
                  earnings
    the link      which CRSP stock is which Compustat firm, and when
    the factors   the monthly Fama-French factor returns, used to measure alpha
    the styles    Ken French's six portfolios by size and P/E, used for style
                  analysis

Type your password yourself. Never paste it into an AI chat, and never ask an
AI tool to run this step for you.

CRSP and Compustat are licensed data. Keep them on your own computer: don't
upload them to an AI chat or to GitHub. (Git already leaves data/ out.)

It downloads only the WRDS files not already in data/: if they are all
there, it skips WRDS and only refreshes the factors and styles, so running it
again does not ask for your password. To download a file again, delete it
from data/ first.

To test your WRDS account first, in a minute and with no download:

    uv run step1_download.py --check

It logs in, checks that your account can read every table this step needs,
and stops.
"""
import datetime
import getpass
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DATA = HERE / "data"
FIRST_YEAR = 1963        # Compustat's coverage starts in the early 1960s
LAST_YEAR = datetime.date.today().year
FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"

# The WRDS tables, and the columns this step reads from each.
TABLES = {
    "crsp.msf_v2": ["permno", "mthcaldt", "mthret", "mthcap", "primaryexch",
                    "siccd", "ticker", "issuernm"],
    "comp.funda": ["gvkey", "datadate", "fyear", "sale", "cogs", "at", "lt",
                   "seq", "ceq", "pstk", "pstkrv", "pstkl", "txditc", "ib"],
    "crsp.ccmxpf_lnkhist": ["gvkey", "lpermno", "linkdt", "linkenddt",
                            "linktype", "linkprim"],
    "crsp.stksecurityinfohist": ["permno", "secinfostartdt", "secinfoenddt",
                                 "siccd"],
}
FILES = {"crsp.msf_v2": "crsp_monthly.parquet",
         "comp.funda": "compustat_annual.parquet",
         "crsp.ccmxpf_lnkhist": "ccm_link.parquet",
         "crsp.stksecurityinfohist": "crsp_sic_history.parquet"}
NAMES = {"crsp.msf_v2": "CRSP monthly stock file",
         "comp.funda": "Compustat annual accounts",
         "crsp.ccmxpf_lnkhist": "The CRSP-Compustat link",
         "crsp.stksecurityinfohist": "CRSP industry codes over time"}


def connect():
    """Log in to WRDS. You type your password; WRDS sends a Duo push."""
    import wrds
    username = input("Your WRDS username: ").strip()
    password = getpass.getpass("Your WRDS password (nothing shows as you type): ")
    print("Now open Duo Mobile on your phone and tap Approve.")
    print("Nothing happens here until you do.")
    db = wrds.Connection(wrds_username=username, wrds_password=password,
                         autoconnect=False)
    # One attempt only. The wrds package's own connect() retries after a
    # failure, asking for the password again, and repeated attempts can get
    # a WRDS account locked; it also hides WRDS's reason for refusing.
    try:
        db._Connection__make_sa_engine_conn(raise_err=True)
    except Exception as error:
        reason = str(error).strip().splitlines()[0] if str(error).strip() else ""
        raise SystemExit("WRDS did not let you in" + (f" ({reason})" if reason
                         else "") + ".\nCheck your username and password, "
                         "approve the Duo push within a minute, and wait a "
                         "few minutes before you try again.")
    print("Connected to WRDS.\n")
    return db


def check_access(db):
    """Stop now, not halfway, if your account cannot read a table or column."""
    for table, columns in TABLES.items():
        try:
            db.raw_sql(f"SELECT {', '.join(columns)} FROM {table} LIMIT 0")
        except Exception as error:
            reason = str(error).strip().splitlines()[0]
            raise SystemExit(f"Could not read {table} ({reason}). "
                             "Tell your instructor.")


def download_crsp(db):
    """CRSP's monthly stock file: ordinary common shares of US firms on the
    NYSE, AMEX and NASDAQ, a decade at a time, so you can see it working."""
    pieces = []
    for start in range(FIRST_YEAR, LAST_YEAR + 1, 10):
        end = min(start + 9, LAST_YEAR)
        print(f"      {start}-{end}", flush=True)
        pieces.append(db.raw_sql(f"""
            SELECT {', '.join(TABLES['crsp.msf_v2'])}
            FROM crsp.msf_v2
            WHERE mthcaldt BETWEEN '{start}-01-01' AND '{end}-12-31'
              AND sharetype = 'NS' AND securitytype = 'EQTY'
              AND securitysubtype = 'COM' AND usincflg = 'Y'
              AND issuertype IN ('ACOR', 'CORP')
              AND primaryexch IN ('N', 'A', 'Q')
              AND conditionaltype = 'RW' AND tradingstatusflg = 'A'
            """, date_cols=["mthcaldt"]))
    return pd.concat(pieces, ignore_index=True)


def download_compustat(db):
    """Compustat's annual accounts, one standard record per firm and year."""
    return db.raw_sql(f"""
        SELECT {', '.join(TABLES['comp.funda'])}
        FROM comp.funda
        WHERE indfmt = 'INDL' AND datafmt = 'STD' AND popsrc = 'D'
          AND consol = 'C' AND datadate >= '{FIRST_YEAR - 2}-01-01'
        """, date_cols=["datadate"])


# [slide: download link]
def download_link(db):
    """The CRSP-Compustat link: which permno is which gvkey, and when."""
    return db.raw_sql("""
        SELECT gvkey, lpermno AS permno, linkdt, linkenddt
        FROM crsp.ccmxpf_lnkhist
        WHERE linktype IN ('LU', 'LC') AND linkprim IN ('P', 'C')
        """, date_cols=["linkdt", "linkenddt"])
# [end]


def download_sic_history(db):
    """Each stock's SIC industry code over time. The monthly file carries
    only today's code, and using it for earlier years would look ahead."""
    return db.raw_sql("""
        SELECT permno, secinfostartdt, secinfoenddt, siccd
        FROM crsp.stksecurityinfohist
        """, date_cols=["secinfostartdt", "secinfoenddt"])


DOWNLOADS = {"crsp.msf_v2": download_crsp, "comp.funda": download_compustat,
             "crsp.ccmxpf_lnkhist": download_link,
             "crsp.stksecurityinfohist": download_sic_history}


def french_text(name):
    """One of Ken French's zipped CSV files, as text."""
    request = urllib.request.Request(FRENCH + name + "_CSV.zip",
                                     headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    return archive.read(archive.namelist()[0]).decode("latin-1")


def french_monthly(text, columns):
    """The first block of monthly rows in one of French's files, renamed by
    `columns` ({French's name: ours}) and turned from percent into decimals."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith(",") and line.split(",")[1].strip())
    header = [h.strip() for h in lines[start].split(",")]
    rows = []
    for line in lines[start + 1:]:
        cells = [c.strip() for c in line.split(",")]
        if len(cells) != len(header) or not (cells[0].isdigit()
                                             and len(cells[0]) == 6):
            break                        # the monthly block has ended
        rows.append(cells)
    table = pd.DataFrame(rows, columns=["month"] + header[1:])
    table["month"] = table["month"].str[:4] + "-" + table["month"].str[4:]
    table = table.set_index("month")[list(columns)].astype(float) / 100
    return table.rename(columns=columns)


def download_french():
    """The factors and the style portfolios, from French's site (no login)."""
    five = french_monthly(french_text("F-F_Research_Data_5_Factors_2x3"),
                          {"Mkt-RF": "mktrf", "SMB": "smb", "HML": "hml",
                           "RMW": "rmw", "CMA": "cma", "RF": "rf"})
    momentum = french_monthly(french_text("F-F_Momentum_Factor"),
                              {"Mom": "umd"})
    factors = five.join(momentum, how="inner")
    factors[["mktrf", "smb", "hml", "rmw", "cma", "umd", "rf"]].to_csv(
        DATA / "factors.csv")
    styles = french_monthly(french_text("6_Portfolios_ME_EP_2x3"),
                            {"BIG HiEP": "large value", "ME2 EP2": "large blend",
                             "BIG LoEP": "large growth",
                             "SMALL HiEP": "small value",
                             "ME1 EP2": "small blend",
                             "SMALL LoEP": "small growth"})
    styles.to_csv(DATA / "styles.csv")
    return factors, styles


def check():
    """Check the French-file reader on a made-up file, worked by hand."""
    # two monthly blocks, as in French's portfolio files (value-weighted, then
    # equal-weighted): only the first may be read
    text = ("Made-up header text\n\n"
            "  Value Weighted Returns -- Monthly\n"
            ",Mkt-RF,SMB,RF\n"
            "202401,   1.50,  -0.20,   0.40\n"
            "202402,  -3.00,   0.10,   0.41\n"
            "\n  Equal Weighted Returns -- Monthly\n"
            ",Mkt-RF,SMB,RF\n"
            "202401,   9.99,   9.99,   9.99\n")
    t = french_monthly(text, {"Mkt-RF": "mktrf", "RF": "rf"})
    assert list(t.index) == ["2024-01", "2024-02"]
    assert list(t.columns) == ["mktrf", "rf"]
    assert abs(t.loc["2024-01", "mktrf"] - 0.015) < 1e-12
    assert abs(t.loc["2024-02", "mktrf"] - -0.03) < 1e-12


def check_account():
    """Log in and check every table, without downloading anything."""
    print("Step 1, account check: log in to WRDS and test access.\n")
    db = connect()
    check_access(db)
    db.close()
    print("Your WRDS account can read every table step 1 needs.")
    print("Next: uv run step1_download.py")


def main():
    if sys.argv[1:] == ["--check"]:
        return check_account()
    print("Step 1: download the data from WRDS. Run it yourself, once: "
          "it takes a few minutes.\n")
    DATA.mkdir(exist_ok=True)
    missing = [t for t in TABLES if not (DATA / FILES[t]).exists()]
    db = None
    if missing:
        db = connect()
        check_access(db)
    parts = len(TABLES) + 1
    for i, table in enumerate(TABLES, 1):
        if table in missing:
            print(f"[{i}/{parts}] {NAMES[table]}")
            DOWNLOADS[table](db).to_parquet(DATA / FILES[table])
        else:
            print(f"[{i}/{parts}] {NAMES[table]}: already in data/")
    if db is not None:
        db.close()
    print(f"[{parts}/{parts}] Factors and style portfolios, from Ken French's site")
    factors, styles = download_french()
    print(f"\nSaved in data/ (factors {factors.index[0]} to {factors.index[-1]}).")
    print("Next: uv run step2_prepare.py")


if __name__ == "__main__":
    check()
    main()

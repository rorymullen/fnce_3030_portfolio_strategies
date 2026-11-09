"""Run steps 3, 4 and 5 for one strategy file.

    uv run run.py my_strategy.py
    uv run run.py examples/gross_profitability.py

The results go in results/<file name>/, ending with factsheet.pdf. Step 1
(the download) runs on its own, once; step 2's tidy data must be there.
"""
import sys
from pathlib import Path

import step3_backtest as step3
import step4_evaluate as step4
import step5_factsheet as step5

HERE = Path(__file__).parent


def run(path):
    """Steps 3, 4 and 5, in order, each checking itself first."""
    step3.check()
    step4.check()
    step5.check()
    strategy = step3.load_strategy(path)
    name = Path(path).stem
    print(f"{strategy.NAME}")
    print("  step 3: forming portfolios...")
    returns, groups, holdings = step3.form_portfolios(step3.load_stocks(),
                                                      strategy)
    step3.save(name, returns, groups, holdings)
    print("  step 4: measuring performance...")
    step4.save(name, step4.evaluate(name, strategy))
    print("  step 5: making the factsheet...")
    return step5.make_factsheet(name, strategy)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "my_strategy.py"
    pdf = run(path)
    print(f"Your factsheet: {pdf.relative_to(HERE)}")

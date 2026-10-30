# Contributing

Fixes to the staking math, new odds formats and better operator signals are welcome. Three constraints keep this repo useful.

## The script stays dependency free

Python 3.8+, standard library only. Run this before opening a pull request:

```bash
python3 -m py_compile arb.py
python3 -m unittest discover -s tests -v
python3 arb.py calc 2.10 2.05; test $? -eq 0
python3 arb.py calc 1.91 1.91; test $? -eq 1
python3 arb.py scan examples/odds.example.csv
python3 arb.py flag examples/bets.example.csv
```

A new signal in `flag` needs a test in `tests/test_arb.py` and a row in the signal table in the README. Keep the weights summing to 1.0 so scores stay comparable.

## Example data is synthetic

Every bookmaker, team, player and account in `examples/` is fictional. A pull request adding real bookmaker feeds, real fixtures with live prices or any customer data will be rejected.

## Scope

This repo explains the math and helps operators review accounts. Pull requests that add bookmaker scraping, automated bet placement or ways to defeat an operator's identity checks are out of scope and will be closed.

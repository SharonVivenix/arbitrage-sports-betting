#!/usr/bin/env python3
"""Arbitrage sports betting toolkit.

Three subcommands, one equation underneath:

  calc   arbitrage betting calculator for one market (stake split, profit)
  scan   find arbitrage across bookmakers in an odds CSV
  flag   operator side: score accounts in a bet log for arbitrage behaviour

Standard library only. Python 3.8+.
"""

import argparse
import csv
import sys
from collections import defaultdict
from fractions import Fraction

# flag: a bet counts as "off market" when its price beats consensus by this much
OFF_MARKET_EDGE = 0.03
# flag: closing line value at or above this counts as the full CLV signal
CLV_CAP = 0.05
# flag: signal weights, they sum to 1.0 so the score stays in 0..1
WEIGHTS = {"off_market": 0.40, "clv": 0.30, "calc_stakes": 0.15, "niche": 0.15}
# flag: accounts with fewer settled bets than this are skipped, not scored
MIN_BETS = 10


def to_decimal(text):
    """Convert decimal (2.10), fractional (11/10) or American (+110, -120) odds."""
    s = str(text).strip()
    if not s:
        raise ValueError("empty odds value")
    if "/" in s:
        dec = 1 + float(Fraction(s))
    elif s[0] in "+-":
        v = float(s)
        if v >= 100:
            dec = 1 + v / 100
        elif v <= -100:
            dec = 1 + 100 / abs(v)
        else:
            raise ValueError(f"American odds must be <= -100 or >= +100: {s}")
    else:
        dec = float(s)
    if dec <= 1:
        raise ValueError(f"odds must pay more than the stake back: {s}")
    return dec


def book_sum(odds):
    """Sum of implied probabilities. Below 1.0 means an arbitrage exists."""
    return sum(1 / o for o in odds)


def split_stakes(odds, total):
    """Stake each outcome in proportion to its implied probability.

    Every outcome then returns the same amount, total / book_sum(odds).
    """
    book = book_sum(odds)
    return [total * (1 / o) / book for o in odds]


def round_stakes(stakes, step):
    return [round(s / step) * step for s in stakes]


def outcome_profits(odds, stakes):
    total = sum(stakes)
    return [s * o - total for s, o in zip(stakes, odds)]


# ---------------------------------------------------------------- calc

def cmd_calc(args):
    odds = [to_decimal(o) for o in args.odds]
    if len(odds) < 2:
        sys.exit("calc needs the odds for every outcome, at least two")
    book = book_sum(odds)
    stakes = split_stakes(odds, args.stake)
    if args.round:
        stakes = round_stakes(stakes, args.round)
    profits = outcome_profits(odds, stakes)
    total = sum(stakes)

    print(f"{'outcome':<8}{'odds':>8}{'implied':>10}{'stake':>11}{'return':>11}{'profit':>10}")
    for i, (o, s, p) in enumerate(zip(odds, stakes, profits), 1):
        print(f"{i:<8}{o:>8.3f}{1 / o:>10.2%}{s:>11.2f}{s * o:>11.2f}{p:>10.2f}")
    print(f"\nbook {book:.2%}   total staked {total:.2f}")
    worst = min(profits)
    if book < 1:
        print(f"arbitrage: worst case profit {worst:.2f} ({worst / total:.2%} of stake)")
    else:
        print(f"no arbitrage: the market is overround, worst case {worst:.2f} ({worst / total:.2%})")
    return 0 if worst > 0 else 1


# ---------------------------------------------------------------- scan

def load_odds(path):
    """Return {(event, market): {outcome: (best_odds, bookmaker)}} plus outcome sets."""
    best = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["event"], row["market"])
            dec = to_decimal(row["odds"])
            cur = best[key].get(row["outcome"])
            if cur is None or dec > cur[0]:
                best[key][row["outcome"]] = (dec, row["bookmaker"])
    return best


def scan(path, min_margin=0.0):
    """Yield one dict per market whose best prices sum below 1 - min_margin."""
    for (event, market), outcomes in load_odds(path).items():
        if len(outcomes) < 2:
            continue
        names = sorted(outcomes)
        odds = [outcomes[n][0] for n in names]
        book = book_sum(odds)
        margin = 1 / book - 1
        if book < 1 and margin >= min_margin:
            yield {
                "event": event,
                "market": market,
                "legs": [(n, outcomes[n][0], outcomes[n][1]) for n in names],
                "book": book,
                "margin": margin,
            }


def cmd_scan(args):
    found = sorted(scan(args.csv, args.min_margin / 100), key=lambda a: -a["margin"])
    if not found:
        print("no arbitrage in this feed")
        return 1
    for arb in found:
        print(f"{arb['event']} | {arb['market']}  book {arb['book']:.2%}  margin {arb['margin']:.2%}")
        stakes = split_stakes([leg[1] for leg in arb["legs"]], args.stake)
        for (name, dec, bookie), stake in zip(arb["legs"], stakes):
            print(f"    {name:<14} {dec:>6.2f} @ {bookie:<10} stake {stake:>9.2f}")
    return 0


# ---------------------------------------------------------------- flag

def is_calculator_stake(stake):
    """Stakes like 487.31 come out of a stake splitter. People type 50 or 25."""
    return round(stake * 100) % 500 != 0


def score_accounts(path):
    bets = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            bets[row["account_id"]].append(row)

    results = []
    for account, rows in bets.items():
        if len(rows) < MIN_BETS:
            continue
        n = len(rows)
        off_market = clv_total = calc = niche = 0
        for r in rows:
            taken = to_decimal(r["odds"])
            consensus = to_decimal(r["consensus_odds"])
            closing = to_decimal(r["closing_odds"])
            off_market += taken >= consensus * (1 + OFF_MARKET_EDGE)
            clv_total += taken / closing - 1
            calc += is_calculator_stake(float(r["stake"]))
            niche += r["market_tier"].strip().lower() == "niche"
        signals = {
            "off_market": off_market / n,
            "clv": clv_total / n,
            "calc_stakes": calc / n,
            "niche": niche / n,
        }
        clv_part = min(max(signals["clv"], 0), CLV_CAP) / CLV_CAP
        score = (
            WEIGHTS["off_market"] * signals["off_market"]
            + WEIGHTS["clv"] * clv_part
            + WEIGHTS["calc_stakes"] * signals["calc_stakes"]
            + WEIGHTS["niche"] * signals["niche"]
        )
        results.append({"account": account, "bets": n, "score": score, **signals})
    return sorted(results, key=lambda r: -r["score"])


def cmd_flag(args):
    results = score_accounts(args.csv)
    print(f"{'account':<11}{'bets':>5}{'off_mkt':>9}{'clv':>8}{'calc_stk':>10}{'niche':>8}{'score':>7}  review")
    flagged = 0
    for r in results:
        hit = r["score"] >= args.threshold
        flagged += hit
        print(
            f"{r['account']:<11}{r['bets']:>5}{r['off_market']:>9.0%}{r['clv']:>8.1%}"
            f"{r['calc_stakes']:>10.0%}{r['niche']:>8.0%}{r['score']:>7.2f}  {'YES' if hit else ''}"
        )
    print(f"\n{flagged} of {len(results)} accounts at or above {args.threshold:.2f}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("calc", help="arbitrage betting calculator for one market")
    c.add_argument("odds", nargs="+", help="best odds per outcome: 2.10, 11/10 or +110")
    c.add_argument("--stake", type=float, default=100.0, help="total to split (default 100)")
    c.add_argument("--round", type=float, metavar="STEP", help="round each stake to a multiple of STEP")
    c.set_defaults(func=cmd_calc)

    s = sub.add_parser("scan", help="find arbitrage across bookmakers in an odds CSV")
    s.add_argument("csv", help="columns: event,market,outcome,bookmaker,odds")
    s.add_argument("--min-margin", type=float, default=0.0, help="ignore arbs under this percent")
    s.add_argument("--stake", type=float, default=100.0, help="total stake for the printed split")
    s.set_defaults(func=cmd_scan)

    f = sub.add_parser("flag", help="score accounts in a bet log for arbitrage behaviour")
    f.add_argument("csv", help="columns: account_id,placed_at,event,market,outcome,stake,"
                               "odds,consensus_odds,closing_odds,market_tier")
    f.add_argument("--threshold", type=float, default=0.5, help="review queue cutoff (default 0.5)")
    f.set_defaults(func=cmd_flag)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

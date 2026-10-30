import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import arb  # noqa: E402

ODDS = os.path.join(ROOT, "examples", "odds.example.csv")
BETS = os.path.join(ROOT, "examples", "bets.example.csv")


class OddsFormats(unittest.TestCase):
    def test_decimal(self):
        self.assertAlmostEqual(arb.to_decimal("2.10"), 2.10)

    def test_fractional(self):
        self.assertAlmostEqual(arb.to_decimal("11/10"), 2.10)
        self.assertAlmostEqual(arb.to_decimal("2/1"), 3.0)

    def test_american(self):
        self.assertAlmostEqual(arb.to_decimal("+110"), 2.10)
        self.assertAlmostEqual(arb.to_decimal("-125"), 1.80)

    def test_rejects_impossible_odds(self):
        for bad in ("1.0", "0.8", "+50", "-99", ""):
            with self.assertRaises(ValueError):
                arb.to_decimal(bad)


class StakeSplit(unittest.TestCase):
    def test_every_outcome_returns_the_same(self):
        odds = [2.60, 3.60, 3.30]
        stakes = arb.split_stakes(odds, 1000)
        self.assertAlmostEqual(sum(stakes), 1000)
        returns = [s * o for s, o in zip(stakes, odds)]
        for r in returns:
            self.assertAlmostEqual(r, 1000 / arb.book_sum(odds))

    def test_two_way_margin(self):
        profits = arb.outcome_profits([2.10, 2.05], arb.split_stakes([2.10, 2.05], 1000))
        self.assertAlmostEqual(min(profits), 37.35, places=2)

    def test_rounding_lowers_the_worst_case(self):
        odds = [2.10, 2.05]
        exact = min(arb.outcome_profits(odds, arb.split_stakes(odds, 1000)))
        rounded = min(arb.outcome_profits(odds, arb.round_stakes(arb.split_stakes(odds, 1000), 50)))
        self.assertLess(rounded, exact)

    def test_overround_market_loses(self):
        profits = arb.outcome_profits([1.91, 1.91], arb.split_stakes([1.91, 1.91], 100))
        self.assertLess(max(profits), 0)


class Scan(unittest.TestCase):
    def test_finds_exactly_the_two_seeded_arbs(self):
        found = {a["event"] for a in arb.scan(ODDS)}
        self.assertEqual(found, {"Harbor City v Northgate", "Player One v Player Two"})

    def test_min_margin_filters(self):
        found = {a["event"] for a in arb.scan(ODDS, min_margin=0.036)}
        self.assertEqual(found, {"Player One v Player Two"})

    def test_picks_best_price_per_outcome(self):
        harbor = next(a for a in arb.scan(ODDS) if a["event"] == "Harbor City v Northgate")
        legs = {name: book for name, _, book in harbor["legs"]}
        self.assertEqual(legs, {"home": "BookC", "draw": "BookA", "away": "BookB"})


class Flag(unittest.TestCase):
    def test_arb_profiles_rank_above_recreational(self):
        results = arb.score_accounts(BETS)
        top_two = {r["account"] for r in results[:2]}
        self.assertEqual(top_two, {"acc-1004", "acc-1006"})
        for r in results[2:]:
            self.assertLess(r["score"], 0.5)

    def test_round_stakes_hide_only_one_signal(self):
        by_id = {r["account"]: r for r in arb.score_accounts(BETS)}
        self.assertEqual(by_id["acc-1006"]["calc_stakes"], 0)
        self.assertGreaterEqual(by_id["acc-1006"]["score"], 0.5)

    def test_calculator_stake_detection(self):
        self.assertTrue(arb.is_calculator_stake(487.31))
        self.assertTrue(arb.is_calculator_stake(212.0))
        self.assertFalse(arb.is_calculator_stake(50))
        self.assertFalse(arb.is_calculator_stake(700.0))


if __name__ == "__main__":
    unittest.main()

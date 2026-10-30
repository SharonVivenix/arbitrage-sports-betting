# Arbitrage Sports Betting

<p align="center">
  <a href="https://www.idenfy.com/">
  </a>
</p>

Every bookmaker price hides a probability, and [arbitrage sports betting](https://www.idenfy.com/blog/arbitrage-sports-betting/) is what happens when two bookmakers disagree about that probability by more than their margins can absorb. Back every outcome at the best available price, size each stake correctly, and the result of the match stops mattering. The bettor gets paid whatever happens, usually 1 to 5 percent of the money staked.

The same inequality sits on both sides of the counter. A bettor uses it to find the gap. An operator uses it to recognise the accounts that only ever bet into that gap. This repository treats arbitrage as one equation and ships [arb.py](arb.py), a dependency free Python script with three subcommands:

| Command | Who runs it | What it does |
|---|---|---|
| `calc` | anyone | arbitrage betting calculator for one market, exact stakes and worst case profit |
| `scan` | analysts, trading teams | finds every arbitrage in an odds feed exported as CSV |
| `flag` | risk and fraud teams | scores accounts in a bet log for the behaviour arbitrage leaves behind |

```bash
python3 arb.py calc 2.10 2.05 --stake 1000
python3 arb.py scan examples/odds.example.csv --stake 1000
python3 arb.py flag examples/bets.example.csv
python3 -m unittest discover -s tests -v
```

Python 3.8 or newer, standard library only. All bookmakers, teams, players and accounts in [examples/](examples/) are fictional.

## What Is Arbitrage Betting?

Arbitrage betting, or arbing, is backing all possible outcomes of one event across different bookmakers so the combined payout beats the combined stake whatever the result. The people who do it are called arbers. A two way tennis market needs two bets, a football match result needs three (home, draw, away), and the trade only works when the best price for each outcome sits at a different bookmaker that has priced the event a little more generously than everyone else.

Two common variants come up in operator risk reviews. Bonus arbitrage uses welcome offers and free bets as one leg, so the "stake" on that side costs the bettor nothing. Cross market arbitrage combines related markets instead of the same one, for example a match winner price at one bookmaker against an Asian handicap line at another.

## The equation

Decimal odds `d` imply a probability of `1 / d`. A bookmaker sets prices so the implied probabilities of every outcome add up to more than 100 percent. The excess is its margin, also called the overround or vig.

```
book    = 1/d1 + 1/d2 + ... + 1/dn       # one price per outcome
book <  1   ->  arbitrage exists
stake_i = total * (1/d_i) / book         # every outcome returns total / book
profit  = total / book - total           # identical whatever the result
```

A single bookmaker quoting both sides of a tennis match at 1.91 has a book of 104.7 percent. Nobody can win that market by backing both sides. Take the best price from each of three bookmakers instead, and the sum can drop below 100 percent. That gap is the whole trade, and it is also why real arbitrage margins are small: each bookmaker's own overround has to be beaten first.

### Odds formats

`arb.py` accepts all three formats anywhere it reads a price.

| Format | Example | Decimal | Conversion |
|---|---|---|---|
| Decimal | `2.10` | 2.10 | as is |
| Fractional | `11/10` | 2.10 | `1 + num/den` |
| American, underdog | `+110` | 2.10 | `1 + value/100` |
| American, favourite | `-125` | 1.80 | `1 + 100/abs(value)` |

American odds need their sign. A bare `150` is read as decimal 150.0, which is almost certainly a typo, and anything at or below 1.0 is rejected.

## Arbitrage betting calculator

`calc` takes the best odds for every outcome of one market and a total stake.

```console
$ python3 arb.py calc 2.10 2.05 --stake 1000
outcome     odds   implied      stake     return    profit
1          2.100    47.62%     493.98    1037.35     37.35
2          2.050    48.78%     506.02    1037.35     37.35

book 96.40%   total staked 1000.00
arbitrage: worst case profit 37.35 (3.73% of stake)
```

Stakes like 493.98 are what a correct split looks like. Bettors know that exact amounts stand out on a bookmaker's risk screen, so many round them. `--round` shows what that costs:

```console
$ python3 arb.py calc 2.10 2.05 --stake 1000 --round 50
outcome     odds   implied      stake     return    profit
1          2.100    47.62%     500.00    1050.00     50.00
2          2.050    48.78%     500.00    1025.00     25.00

book 96.40%   total staked 1000.00
arbitrage: worst case profit 25.00 (2.50% of stake)
```

The guarantee survives, but a third of it went into the rounding. On a thinner market the rounding alone can push one outcome into a loss, and the script exits with status 1 whenever the worst case is not positive, so it can sit inside a shell pipeline.

### The textbook example, sized correctly

Introductory guides often use something like Team A at 2/1 with one bookmaker and Team B at 3/1 with another, staked as 100 and 66.67. Run it through the calculator:

```console
$ python3 arb.py calc 2/1 3/1 --stake 166.67
outcome     odds   implied      stake     return    profit
1          3.000    33.33%      95.24     285.72    119.05
2          4.000    25.00%      71.43     285.72    119.05

book 58.33%   total staked 166.67
arbitrage: worst case profit 119.05 (71.43% of stake)
```

Two things stand out. The balanced split pays 119.05 either way, where the 100 and 66.67 split pays 133.33 or 100, so the original stakes left money on one side. And a book of 58 percent means both teams are priced as underdogs at the same time. Two bookmakers would have to misprice a game by tens of points for that to happen, so treat it as an illustration of the mechanism, not a target. A live arb feed looks like the 96.4 percent book above.

## Scanning an odds feed

When do arbitrage opportunities appear? Mostly in four situations, and each one is visible in an odds feed:

1. **Stale prices.** A bookmaker reacts late to team news, an injury or a weather change, and its price sits away from the market for minutes.
2. **Live betting.** In play prices in tennis and basketball move every few seconds, and not every bookmaker moves at once.
3. **Niche markets.** Lower leagues, youth fixtures and qualifiers get less trading attention, so mispricing lasts longer than on a top flight match.
4. **Promotional pricing.** A bookmaker boosts a price to win customers and pushes it above where the rest of the market trades.

`scan` reads a CSV with one row per price (`event,market,outcome,bookmaker,odds`), keeps the best price per outcome, and prints every market whose book falls under 100 percent, largest margin first.

```console
$ python3 arb.py scan examples/odds.example.csv --stake 1000
Player One v Player Two | match_winner  book 96.40%  margin 3.73%
    player_one       2.10 @ BookA      stake    493.98
    player_two       2.05 @ BookB      stake    506.02
Harbor City v Northgate | match_result  book 96.54%  margin 3.58%
    away             3.30 @ BookB      stake    313.88
    draw             3.60 @ BookA      stake    287.73
    home             2.60 @ BookC      stake    398.39
```

The example feed holds four markets. The moneyline and the total goals market look tempting line by line but their best prices still sum to 101.8 and 101.3 percent, so the scanner skips them. Use `--min-margin 2` to ignore anything under 2 percent, which is roughly where fees, rounding and price movement eat the rest.

For an operator the same scan answers a different question: which of our prices are the outlier leg in an arbitrage right now? A price that keeps showing up as one leg of a live arb is a price that is about to attract the wrong customers.

## Sports betting arbitrage from the operator side

Arbers do not show up in a bet log as people who win a lot. Plenty of them lose individual bets at your book, because the winning leg sat somewhere else. What they leave behind is a pattern of *where* they bet, measured against the rest of the market.

`flag` reads a settled bet log and computes four signals per account:

| Signal | Column(s) used | Why it points to arbitrage |
|---|---|---|
| `off_mkt` | `odds`, `consensus_odds` | share of bets taken at least 3 percent above the market consensus price. An arber only bets with you when you are the outlier |
| `clv` | `odds`, `closing_odds` | mean closing line value, `odds / closing_odds - 1`. Recreational customers average slightly negative. Arbers take prices that the market later corrects |
| `calc_stk` | `stake` | share of stakes that are not a multiple of 5, the fingerprint of a stake splitter |
| `niche` | `market_tier` | share of bets on lower leagues, youth fixtures and qualifiers, where prices stay wrong longest |

```console
$ python3 arb.py flag examples/bets.example.csv
account     bets  off_mkt     clv  calc_stk   niche  score  review
acc-1004      20     100%    6.3%      100%     45%   0.92  YES
acc-1006      20     100%    6.4%        0%     50%   0.77  YES
acc-1001      20       0%   -1.4%        0%     20%   0.03
acc-1002      20       0%   -1.0%        0%     15%   0.02
acc-1003      20       0%   -0.8%        0%     15%   0.02
acc-1005      20       0%   -0.7%        0%      5%   0.01

2 of 6 accounts at or above 0.50
```

The score is a weighted sum in the range 0 to 1, with weights and cutoffs as named constants at the top of `arb.py`. `acc-1006` is the reason for that design. It rounds every stake to the nearest 10, which zeroes the stake signal completely, and it is still flagged, because rounding a stake does nothing to the price it was placed at. Much of the advice on spotting arbers leans on odd stake amounts. That is the weakest of the four signals and the easiest to fake. Price relative to consensus and closing line value are what an arber cannot hide without giving up the arb.

`consensus_odds` is whatever reference your trading team already uses, an average across a set of bookmakers or a sharp book's price captured at bet time. `closing_odds` is the last price before the event started. If your platform does not store either, that is the first gap to close.

### What the flag does not decide

A high score puts an account in a review queue. It is not proof of anything, and a sharp bettor with genuine skill produces a similar footprint. Each operator then picks a response under its own terms and conditions, typically one of these:

- **Stake limits** on the account, per bet or per period
- **Bet voiding** where the price was a palpable error, such as reversed odds
- **Account closure**, with the remaining balance returned under the published terms

Some bookmakers, usually those that price off the sharpest market, accept arbitrage traffic on purpose and use it to correct their own lines faster. Which response fits is a commercial decision, not a technical one.

### What a single book cannot see

Every signal above is computed per account. Once an arber is limited, the usual next move is a new account, often opened under a relative's or a friend's identity and funded from a different card. Inside one bet log that shows up as a brand new customer with a clean history, and every per account model starts from zero again.

That is where the problem moves from odds to identity, and it is the same problem as [multi accounting](https://www.idenfy.com/blog/multi-accounting/) for bonus abuse. Document verification and a liveness check at signup tie the account to one real person, and repeating face authentication at withdrawal confirms that the person collecting the winnings is the one who opened the account. iDenfy's [identity verification for gambling](https://www.idenfy.com/identity-verification-for-gambling/) covers that layer together with AML screening and proxy detection. iDenfy provides the verification step. The operator keeps its licence obligations and decides what to do with a match.

## Is arbitrage betting legal?

In most regulated betting markets, placing arbitrage bets is not an offence. It is also not protected. Bookmaker terms almost always reserve the right to limit or close accounts and to void bets on obvious pricing errors, and a gambling licence does not oblige an operator to keep taking an arber's bets. Rules vary by jurisdiction and change over time, so check the local framework and the specific bookmaker terms. Nothing in this repository is legal or financial advice.

Arbitrage is also less reliable than the "guaranteed profit" phrase suggests. Margins are thin, one leg can be voided after the other has already been placed, prices move between the first and second bet, and accounts that arb consistently get limited, which caps how far the strategy scales.

## Bet log format

`flag` expects one row per settled bet:

```csv
account_id,placed_at,event,market,outcome,stake,odds,consensus_odds,closing_odds,market_tier
acc-1004,2026-09-05T16:32,Ostrava B v Brnik,match_result,home,490.83,1.87,1.75,1.73,niche
```

`odds`, `consensus_odds` and `closing_odds` accept any of the three formats. `market_tier` is `main` or `niche`, and anything other than `niche` counts as main. Accounts with fewer than 10 bets are skipped instead of being scored on noise.

## Repository layout

```
arb.py                       calc, scan and flag subcommands
examples/odds.example.csv    four markets, three bookmakers, two arbs
examples/bets.example.csv    120 settled bets, six accounts, two arbers
tests/test_arb.py            14 unit tests covering odds parsing, staking, scanning, scoring
```

## Contributing and credits

Corrections to the math, new odds formats and better operator signals are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

The concepts here are adapted from iDenfy's guide [How Can You Detect Arbitrage in Sports Betting?](https://www.idenfy.com/blog/arbitrage-sports-betting/), and iDenfy is the publisher of that source. The calculator, the scanner, the scoring model and the example data are independent work. Nothing in this repo is legal or financial advice.

## License

MIT. See [LICENSE](LICENSE).

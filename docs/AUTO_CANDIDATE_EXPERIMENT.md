# Automatic candidate generation experiment

## Goal

Replace the manually curated tariff-transition shortlist with a reproducible
offline generator without changing the submitted `agent.py` until the new
policy proves robust.

## Method

`experiments/candidate_generator.py` derives transition priors from
`data/change_tariff.csv` and the current scoring audience:

1. Keep rows with previous ARPU of at least 100 and clip relative ARPU change
   to the documented `[-1, 3]` range.
2. Aggregate each `(current tariff, target tariff, ARPU segment)` transition.
3. Shrink small-sample effects toward the matching current-tariff/ARPU cell.
4. Smooth transition shares toward the global target-tariff distribution.
5. Rank positive hypotheses by estimated reachable push value. Package
   compatibility is capped at a five-percent tie-breaker.
6. During exploration, test distinct audience cells before alternative target
   tariffs for the same cell.

The generated shortlist contains 30 hypotheses; the experimental agent still
uses the same 2,000 pilot contacts as production: 12 initial pilots of 100 and
five confirmation pilots of 160.

## Stress result

Each row contains 50 runs (five shifted models by ten pilot seeds).

| Scenario | Production median | Generated median | Production p10 | Generated p10 | Production min | Generated min |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Base | 3,305,739 | 3,161,210 | 2,877,180 | 2,208,182 | 2,213,979 | 2,190,593 |
| Effect noise | 3,145,255 | 3,081,308 | 2,307,413 | 2,226,404 | 2,076,365 | 1,976,541 |
| Sign flip | 3,085,472 | 2,983,250 | 1,977,923 | 2,016,677 | 1,912,143 | 1,836,292 |
| Ranking shuffle | 253,230 | 213,765 | 56,553 | 27,342 | -31,332 | -294,728 |
| Weak history | 887,849 | 976,579 | 565,254 | 633,672 | 390,501 | 386,386 |
| Combined shift | 2,178,464 | 2,418,702 | 1,568,353 | 1,604,645 | 1,272,394 | 1,525,451 |

## Decision

Keep the current production shortlist for the next deploy. The generator is
promising under weak-history and combined-shift scenarios, but it gives up
about 4.4% median value in the base case and has a worse ranking-shuffle tail.
The experiment stays available for the next iteration, where the generated
and curated priors can be blended and re-evaluated before promotion.

Reproduce the comparison from the repository root:

```bash
python experiments/stress_eval.py --agents current,generated --model-seeds 5 --pilot-seeds 10
```

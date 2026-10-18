# How the 25 facilities were selected

The facilities of OBSCURA-Open-25 were selected from a larger set of candidate facilities by a quality score and a few caps. The rule is stated here so that the effect of the selection can be judged. The candidate list itself is not published.

## Score

For each candidate, six parts, each scaled from 0 to 1, were combined with fixed weights:

| Part | Definition | Weight |
|---|---|---|
| samples | number of samples, capped at 60, divided by 60 | 0.25 |
| presence | mean share of samples with methane, NO2 and CO measured | 0.25 |
| clear | 1 minus mean chip cloud share divided by 0.20 (floored at 0) | 0.15 |
| valid | mean valid-pixel share times (1 minus share of zero pixels) | 0.10 |
| season | months of the year with at least one sample, divided by 12 | 0.15 |
| box | 1 minus the distance of the box side from 3.5 km, divided by 4.5 km (mid-sized boxes frame a facility best) | 0.10 |

## Eligibility and caps

A candidate had to have at least 30 samples, methane present in at least 25% of them, and samples in at least 8 months of the year. Eligible candidates were taken in order of score until 25 were chosen, skipping a candidate when its country already had 3 facilities, its world region 8, or its facility type group 10.

## What this means for use

* The selected facilities are better covered, less cloudy and more regularly observed than a typical industrial facility, and their image boxes are mid-sized. The data cannot say how often a retrieval exists at a cloudier or sparser site.
* The caps spread the facilities over countries and regions but do not make them a representative sample of the world's industry.
* The score does not look at the targets' values, only at how often and how cleanly they were measured. It cannot by construction favour facilities with high emissions, but it does favour facilities where measurement is easy.
* A selection like this can make a model's task look easier than it will be on an average site. The comparison of a random and a facility-grouped split in `EVALUATION.md` is a comparison within these 25 facilities and should not be read as a global estimate.
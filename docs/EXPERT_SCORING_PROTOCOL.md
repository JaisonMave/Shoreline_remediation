# Expert Scoring Protocol

## Purpose

The suitability model is trained on rule-generated labels, so it can only repeat the rules. Scores from
shoreline response experts are the first real labels. This protocol makes those scores comparable between
experts and tells you whether they agree well enough to train on.

## Steps

1. **Build the sheet.** Run `python -m src.shoreline_remediation.expert_scoring sheet`. It writes
   `data/expert_scoring_sheet.csv`: 30 scenarios spread across the eight shoreline types, with one empty
   column for each of the 15 treatments. The rule-generated scores are left out so they cannot anchor
   anyone.
2. **Recruit at least three experts** with shoreline cleanup or SCAT experience. Two is the minimum for
   measuring agreement. Record each expert's background, but keep names out of the data files.
3. **Score independently.** Each expert fills in a separate copy and does not see the others' scores or
   the model's ranking.
4. **Use the scale below.** Score every treatment for every scenario, including ones that are clearly
   unsuitable.
5. **Combine.** Run `python -m src.shoreline_remediation.expert_scoring combine expert_a.csv expert_b.csv
   expert_c.csv`. It writes the mean scores, the agreement table and the list of disputed items.
6. **Discuss disputed items once.** For pairs where experts differ by more than 2 points, hold one
   discussion, let experts revise if they wish, and keep both the original and revised scores.
7. **Train only on treatments with acceptable agreement** (ICC of 0.5 or higher). For the others, report
   the disagreement; it is a finding about the state of practice.

## Scale

| Score | Meaning |
| --- | --- |
| 0 | Should not be used here: infeasible, or would cause more harm than the oil |
| 1-3 | Poor option: likely ineffective or damaging; use only if nothing else is possible |
| 4-6 | Acceptable with conditions: workable, with clear drawbacks or a need for close supervision |
| 7-8 | Good option: effective with manageable side effects |
| 9-10 | Preferred option: what you would recommend first for this scenario |

Ask experts to judge net environmental benefit: oil removed, weighed against damage from the treatment,
waste generated and worker safety. Ask them to use the `notes` column where a missing piece of information
would change the score.

## Reading the agreement table

Agreement is measured per treatment with ICC(2,1), the two-way random-effects, absolute-agreement
intraclass correlation (Shrout and Fleiss 1979). A common reading (Koo and Li 2016): below 0.5 poor, 0.5 to
0.75 moderate, 0.75 to 0.9 good, above 0.9 excellent.

## After scoring

- Retrain the suitability models on `data/expert_labels.csv`, using the between-expert standard deviation
  as the noise level for each label.
- Re-run `validation/historical_validation.py` and `validation/feature_validation.py`. With expert labels
  these become independent checks, because the labels no longer come from the rules being tested.
- Thirty scenarios are enough to measure agreement and to check the rules. They are few for training a
  model on eight inputs, so add scenarios in the regions where experts disagree with the rules most.

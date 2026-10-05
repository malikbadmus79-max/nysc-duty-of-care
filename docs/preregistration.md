# Pre-registration

Pre-registered analysis plan for the study of duty of care to NYSC corps members.

| Item | Value |
|------|-------|
| Status | Draft. Frozen by the git tag `prereg-v1` before the incident register is analysed. |
| Draft date | 5 October 2026 |
| Data collected at draft date | Policy documents only. No incident data have been collected or analysed. |
| Amendments | Any change after the tag is listed in section 8 with date, reason and whether it was made before or after outcome data were seen. |

## 1. Hypotheses

| ID | Hypothesis | Direction |
|----|------------|-----------|
| H1 | Incidents in the North West and North East receive fewer news articles per incident than incidents in the South West, South East and South South. | One-sided |
| H2 | The share of incidents occurring within 7 days of an official camp-opening or passing-out date is larger than the share of calendar days covered by those windows. | One-sided |
| H3 | Incident rates per 10,000 corps members sworn in differ across states. | Two-sided |
| H4 | State incident rates for corps members are positively correlated with state rates of general kidnapping per 100,000 population. | One-sided |
| H5 | Security-related NYSC allocations per corps member, in constant 2024 naira, show no increase between 2018 and 2026. | Descriptive |

## 2. Units and samples

The unit is the incident, defined in `docs/coding_protocol.md`. The register covers 1 January 2010 to 31 December 2026. State-level analyses use the 36 states and the FCT. H2 uses incidents with day-level dates in the stages `travel_to_camp`, `camp`, `travel_to_ppa` and `passing_out` [A01, A04].

## 3. Measures

| Measure | Definition | Code |
|---------|------------|------|
| Articles per incident | Number of distinct articles in the eight searched outlets that report the incident, within 30 days of the event date | `data/processed/incidents.csv` (`n_articles`) |
| Travel window | Days within 7 days either side of an official camp-opening or passing-out date | `nysc_safety.travel_window.window_days` |
| Exposure | Corps members sworn in at the state's orientation camp in the year [A02] | `data/processed/exposure_by_state.csv` |
| Incident rate | Incidents per 10,000 exposed, with exact Poisson 95% interval | `nysc_safety.rates.rate` |
| General kidnapping rate | Kidnapping incidents per 100,000 population, from Nigeria Watch [S09] and from the coded news series | `data/processed/general_kidnapping_by_state.csv` |
| Real allocation per corps member | Security-related allocation in constant 2024 naira divided by corps members mobilised in the year | `data/processed/budget_lines.csv` |

## 4. Tests

| Hypothesis | Test | Decision rule |
|------------|------|---------------|
| H1 | Mann-Whitney U test of articles per incident, northern zones (North West and North East) against southern zones (South West, South East, South South); Spearman correlation of state shares of incidents and state shares of articles as a supporting measure | Supported if p < 0.05 and the median for the northern zones is lower |
| H2 | One-sided exact binomial test of incidents inside windows against the share of calendar days covered (`nysc_safety.travel_window.travel_window_test`), 2010 to 2026 | Supported if p < 0.05 |
| H3 | Poisson regression of state incident counts with log exposure as offset; likelihood-ratio test of the state terms against an intercept-only model; negative binomial model if the Pearson dispersion statistic exceeds 1.5 | Supported if p < 0.05 |
| H4 | Spearman rank correlation of state incident rates with state general kidnapping rates, computed separately for each comparison series | Supported if rho > 0 and p < 0.05 in the coded news series; the Nigeria Watch result is reported alongside |
| H5 | Year-by-year series and the change from 2018 to 2026 in constant 2024 naira | Reported descriptively; no significance test |

All tests use alpha = 0.05. H1 to H4 are reported with effect sizes and confidence intervals. No correction for multiple testing is applied because each hypothesis addresses a separate question; all results are reported whether or not they are significant.

## 5. Reliability threshold

A random sample of 20% of incidents, with a minimum of 30, is double-coded. If Cohen's kappa for lifecycle stage, harm type or member status is below 0.70, the coding protocol is revised, the full register is recoded for that variable, and a new sample is double-coded. Each round is reported.

## 6. Exclusions and robustness checks

- Incidents with month or year precision are excluded from H2 and counted in the report [A01].
- H2 is repeated with `personal_travel` incidents included [A04].
- H3 and H4 are repeated with a two-year exposure window [A02].
- H3 and H4 are repeated without the five states with the most incidents, to check that results do not depend on them.
- States with fewer than 1,000 corps members sworn in across the period are excluded from rate rankings and listed.

## 7. Analyses that are exploratory

Any analysis not listed above, including breakdowns by sex, by batch and by year, is labelled exploratory in all outputs.

## 8. Amendments

No amendments as of the draft date.

# Duty of Care to NYSC Corps Members in an Era of Insecurity

An assessment of how far the rules and resources of the National Youth Service Corps (NYSC) protect corps members from kidnapping and other serious harm, and of where in the service year and in which states the risk is highest.

Status, 5 October 2026: repository set up, analysis plan and pre-registration drafted. Policy audit: duty-of-care scores assigned (current framework 12 of 36; with the June 2026 reform 14 of 36), with a sensitivity check on borderline scores. Pre-registration frozen (git tag `prereg-v1`). Incident register in progress: 96 incidents from 2011 to 2026 coded and published in `data/processed/incidents.csv` (35 kidnappings, 23 killings, 18 road crashes, 9 physical assaults, 3 robberies, 3 sexual-violence incidents and 5 other harms), from an archive search of 6,364 articles in Premium Times, Daily Trust and Channels Television and targeted searches of other outlets; 9 candidate incidents await verification. Exposure modelled for all 37 states from 208 reported orientation-course figures and national totals (`data/processed/exposure_by_state.csv`) [A09, A10]. NYSC calendar of camp-opening, camp-closing and passing-out dates for 74 batch-streams, 2010 to 2026 (`data/processed/nysc_calendar.csv`) [A11].

## Questions

1. How far do the NYSC Act, bye-laws, directives and the June 2026 reform package meet the duty-of-care standard published by the Global Interagency Security Forum?
2. Where, when and at which stage of the service year are corps members harmed, and does public attention follow the incidents?
3. Which states carry the highest risk once the number of corps members deployed is taken into account, and does that risk track general kidnapping?
4. Did security-related NYSC funding per corps member change in real terms between 2018 and 2026?

Hypotheses H1 to H5 and their tests are fixed in [`docs/preregistration.md`](docs/preregistration.md).

## Method

| Phase | Method | Main output |
|-------|--------|-------------|
| 1 | Policy audit: 12-criterion duty-of-care scorecard, scored for the framework before and after the June 2026 reform | `docs/policy_audit.md` |
| 2 | Incident register, 2010 to 2026, coded from national news outlets with AI assistance under a published coding protocol, with a coding note for each incident | `data/processed/incidents.csv` |
| 3 | Salience gap, travel-window test, exposure-adjusted rates and comparison with general kidnapping (Nigeria Watch and a news series coded the same way) | Notebooks 02 and 03 |
| 4 | Budget audit, 2018 to 2026, in constant 2024 naira | Notebook 04 |

Full plan and limitations: [`docs/analysis_plan.md`](docs/analysis_plan.md).

## Repository

| Path | Contents |
|------|----------|
| `docs/` | Analysis plan, pre-registration, coding protocol, policy audit, source log, assumptions and data conflicts |
| `data/raw/`, `data/interim/`, `data/processed/` | Downloads, working files and analysis-ready data |
| `src/nysc_safety/` | Python package: archive search, coding scheme validation, register build, rates, travel-window test, scorecard and its sensitivity check |
| `tests/` | pytest tests |
| `notebooks/` | Numbered analysis notebooks |
| `reports/` | Figures and maps |
| `app/` | Streamlit dashboard |

## Standards

Every figure carries a source ID that matches [`docs/sources.md`](docs/sources.md). Disagreements between sources are logged in [`docs/data_conflicts.md`](docs/data_conflicts.md), and assumptions in [`docs/assumptions.md`](docs/assumptions.md). Victim names are not stored, in line with the Nigeria Data Protection Act 2023.

## Running the code

Python 3.12.

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
pytest
python -m nysc_safety.download
python -m nysc_safety.news_search
python -m nysc_safety.register
python -m nysc_safety.exposure
python -m nysc_safety.camp_calendar
python -m nysc_safety.population
```

`download` saves the primary documents in the source log to `data/raw/pdfs/`. `news_search` runs the logged archive search and writes the article index to `data/interim/`; it takes about 30 minutes. `news_search --series general` runs the general kidnapping search used for H4. Each outlet's results are saved to `data/interim/<series>_parts/` as soon as the outlet is finished, and a rerun skips outlets already saved; `--force` searches every outlet again. `register` builds `data/processed/incidents.csv` from the working register and the screening files. `exposure` builds `data/processed/exposure_by_state.csv` from the course figures and national totals in `data/interim/exposure/`. `camp_calendar` builds `data/processed/nysc_calendar.csv` from the dated reports in `data/interim/calendar/`. `population` extracts projected population by state, 2007 to 2022, from the National Population Commission projections into `data/interim/population_by_state.csv`, with a cross-check against the National Bureau of Statistics forecasts.

## Author

Malik Badmus, BSc Sociology, University of Ilorin. [GitHub](https://github.com/malikbadmus79-max) · [LinkedIn](https://linkedin.com/in/malik-badmus)

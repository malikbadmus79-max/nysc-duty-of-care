# CLAUDE.md

Project context and working rules for Claude Code in the `nysc-duty-of-care` repository.

## Project

Working title: Duty of Care to NYSC Corps Members in an Era of Insecurity.

Research question: how far the rules and resources of the National Youth Service Corps (NYSC) meet a recognised standard of duty of care to corps members, and where in the service year and in which states corps members face the highest risk of kidnapping and other serious harm.

| ID | Question | Testable prediction |
|----|----------|---------------------|
| H1 | Salience gap | Media attention per incident is unequal across geopolitical zones; incidents in the North West and North East receive fewer articles per incident than incidents in the South |
| H2 | Travel window | A larger share of incidents falls within 7 days of official camp-opening and passing-out dates than the share of calendar days those windows cover |
| H3 | Exposure-adjusted risk | Incident rates per 10,000 corps members deployed differ by state, and state rankings differ from rankings by raw counts |
| H4 | Relative risk | State-level incident rates for corps members are positively associated with state-level rates of general kidnapping |
| H5 | Resources | Security-related NYSC allocations per corps member did not rise in real terms between 2018 and 2026 |

Scope: harms to prospective and serving corps members in Nigeria, 2010 to 2026, with a focus on kidnapping. Unit of analysis: the incident, aggregated to state and year. Policy instruments in force at any point in the period and the reform package approved by the Federal Executive Council in June 2026 are in scope. Non-security welfare matters (allowance levels, accommodation quality) are out of scope except where they affect exposure to harm.

Phases:

1. Policy audit and duty-of-care scorecard (`docs/policy_audit.md`, `data/processed/policy_scorecard.csv`)
2. Incident register built from news reports (`data/processed/incidents.csv`, `docs/coding_protocol.md`)
3. Risk analysis: salience gap, travel window, exposure-adjusted rates and comparison with general kidnapping (`notebooks/02_incidents.ipynb`, `notebooks/03_risk.ipynb`)
4. Budget audit, 2018 to 2026, inflation-adjusted (`notebooks/04_budget.ipynb`)
5. README, policy brief, Streamlit dashboard and public write-up

The analysis plan is fixed in `docs/preregistration.md` and committed, with a git tag, before any outcome data are analysed.

## Repository layout

| Path | Contents |
|------|----------|
| `data/raw/` | Untouched downloads. Never edited in place. |
| `data/interim/` | Partly cleaned intermediate files and coding sheets |
| `data/processed/` | Analysis-ready CSVs |
| `docs/analysis_plan.md` | Project plan, data sources, methods and limitations |
| `docs/preregistration.md` | Pre-registered hypotheses, measures and tests |
| `docs/coding_protocol.md` | Codebook for the incident register |
| `docs/policy_audit.md` | Duty-of-care scorecard criteria, evidence and scores |
| `docs/sources.md` | Source log with IDs S01, S02, ... |
| `docs/data_conflicts.md` | Log of disagreements between sources and how each is handled |
| `docs/assumptions.md` | Log of assumptions with IDs A01, A02, ... |
| `notebooks/` | Numbered analysis notebooks |
| `src/nysc_safety/` | Importable Python package with all reusable logic |
| `tests/` | pytest tests for `src/nysc_safety/` |
| `reports/figures/` | Saved charts (PNG and HTML) |
| `reports/maps/` | Saved maps (HTML) |
| `app/` | Streamlit application |

## Data rules

- Every figure in `data/processed/` carries a `source_id` column that matches an entry in `docs/sources.md`.
- Source log columns: ID, title, publisher, author, publication date, access date, URL, type, reliability (High, Medium, Low), notes.
- Reliability scale: High for primary official documents (statutes, gazettes, budgets, official NYSC publications); Medium for official statements reported by established news outlets and for original reporting by established outlets; Low for unattributed figures, blogs and secondary aggregators.
- Where two sources report different values for the same metric and period, both values are kept and the conflict is recorded in `docs/data_conflicts.md` with its resolution.
- Assumptions are recorded in `docs/assumptions.md` and referenced by ID wherever they are used in code, notebooks or reports.
- Derived values state the calculation and the period used.
- Raw files are never overwritten. Cleaning steps write new files to `data/interim/` or `data/processed/`.

## Privacy and legal rules

- The Nigeria Data Protection Act 2023 applies. No name of a victim, relative or witness appears in any committed data field, note, headline or text, even where published in news reports. In headlines kept in committed files, such names are replaced with "[name withheld]".
- URLs of published articles cited as evidence are kept as citations: in `docs/sources.md`, the incident register and the screening and checking files that cite specific articles. A URL can contain a name in its slug; the URL is kept unchanged because it is needed to verify the finding.
- The large article indexes from the archive searches are committed with outlet, date, article ID, queries and coded fields only. Their URLs and headlines are kept in git-ignored local `headlines/` folders (`nysc_safety.headlines`). Nigeria Watch event titles and raw result pages are kept locally in the same way.
- Each incident carries an anonymous identifier (`INC0001`, ...). Location is kept at local government area level at the finest.
- Full text of news articles is not committed.
- Tests fail if a committed CSV file other than the reviewed citation files has a headline, title or URL column.
- Officials are named only when acting in an official capacity and only where a documented public source names them in connection with the specific statement.

## Code rules

- Python 3.12 in a virtual environment at `.venv/`. Dependencies are listed in `requirements.txt`.
- Reusable logic lives in `src/nysc_safety/`. Notebooks import from the package and contain analysis and narration, not long function definitions.
- Every module in `src/nysc_safety/` has tests in `tests/`. `pytest` passes before each commit.
- Functions have type hints and short docstrings.
- File paths are built with `pathlib` relative to the repository root, so code runs on Windows and Linux.
- Web requests use a descriptive User-Agent, a delay of at least 2 seconds between requests to the same site, and respect `robots.txt`.
- API keys are read from a `.env` file through `python-dotenv`. `.env` is never committed.
- Charts are saved to `reports/figures/` with descriptive file names and include a source line naming the source IDs.

## Writing style for repository files

- Neutral, factual, third-person wording. No first or second person.
- No placeholder text, no "TODO" in committed documents, no bold lead-ins in bullet lists, no rhetorical questions.
- Facts carry a source ID in square brackets, for example [S03]. Assumptions carry an assumption ID, for example [A02].
- Numbers use thousands separators and state units and period.

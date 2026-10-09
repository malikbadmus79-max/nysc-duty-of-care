# Reproducing the results

Python 3.12. Commands are for Windows PowerShell, run from the repository root.

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
python -m nysc_safety.nigeria_watch
python -m nysc_safety.gazetteer
python -m nysc_safety.general_kidnapping
python -m nysc_safety.budget
streamlit run app/streamlit_app.py
```

`download` saves the primary documents in the source log to `data/raw/pdfs/`. `news_search` runs the logged archive search and writes the article index to `data/interim/`, with the URLs and headlines in a local `headlines/` folder that is not committed; it takes about 30 minutes. `general_kidnapping` needs these local headline files, so on a fresh copy of the repository `news_search --series general` is run first. `news_search --series general` runs the general kidnapping search used for H4. Each outlet's results are saved to `data/interim/<series>_parts/` as soon as the outlet is finished, and a rerun skips outlets already saved; `--force` searches every outlet again. `register` builds `data/processed/incidents.csv` from the working register and the screening files. `exposure` builds `data/processed/exposure_by_state.csv` from the course figures and national totals in `data/interim/exposure/`. `camp_calendar` builds `data/processed/nysc_calendar.csv` from the dated reports in `data/interim/calendar/`. `population` extracts projected population by state, 2007 to 2022, from the National Population Commission projections into `data/interim/population_by_state.csv`, with a cross-check against the National Bureau of Statistics forecasts. `nigeria_watch` reads the Nigeria Watch event list for "kidnapped" with the state of each event and writes `data/processed/nigeria_watch_kidnapping_by_state.csv`. `gazetteer` builds the place-name list used to assign states to headlines, and `general_kidnapping` builds the general kidnapping series from the archive search. `budget` extracts the NYSC line items from the budget documents in `data/raw/pdfs/`, page by page, checks them against the printed NYSC totals and writes `data/processed/budget_lines.csv`. The last command opens the dashboard.

Back to the [README](../README.md).

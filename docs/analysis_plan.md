# Analysis plan

Duty of Care to NYSC Corps Members in an Era of Insecurity. Plan dated 5 October 2026.

## 1. Background

The National Youth Service Corps (NYSC) Act provides for a year of national service by graduates, with the Directorate assigning members to states and State Governing Boards deploying them within each state [S03]. Section 8 of the NYSC Act gives Local Government Committees a duty to ensure the security of corps members [S03]. Since 2010, prospective and serving corps members have been killed and kidnapped while travelling to camp, at places of primary assignment and in host communities. NYSC leadership has responded with travel advisories, including a ban on night travel and guidance to shelter at military barracks [S07, S08]. In June 2026 the Federal Executive Council approved a reform package that includes risk-sensitive deployment and a national grading system for camps, and directed the amendment of the NYSC Act [S04, S05].

No public dataset records harms to corps members, and no published assessment measures NYSC rules against an external duty-of-care standard. This project builds both.

## 2. Research questions

1. How far do the NYSC Act, bye-laws, circulars and the 2026 reform package meet the duty-of-care obligations and security risk management elements set out by the Global Interagency Security Forum [S01, S02]?
2. Where, when and at which stage of the service year are corps members harmed, and how does the pattern compare with where public attention goes?
3. After adjusting for the number of corps members deployed, which states carry the highest risk, and how does that risk relate to the general level of kidnapping in each state?
4. Did security-related NYSC funding per corps member change in real terms between 2018 and 2026?

Hypotheses H1 to H5, their measures and their tests are fixed in `docs/preregistration.md`.

## 3. Phase 1: policy audit and duty-of-care scorecard

The scorecard has 12 criteria (D1 to D12) adapted from the six duty-of-care obligations and ten security risk management elements in S01 and the duty-of-care cycle in S02. Each criterion is scored 0 to 3 for two frameworks: the framework in force before the June 2026 reform, and the reform package as announced. Scoring rules, evidence and scores are recorded in `docs/policy_audit.md` and `data/processed/policy_scorecard.csv`.

Documents in scope:

- NYSC Act, Cap. N84, Laws of the Federation of Nigeria 2004 [S03]
- NYSC Bye-laws (current revised edition)
- Directives, circulars and public advisories from the Directorate on travel, security and redeployment [S07, S08]
- Redeployment and exemption rules, including published grounds for relocation
- The June 2026 reform package and any bill or amendment that follows [S04, S05, S06]

## 4. Phase 2: incident register, 2010 to 2026

The register lists every incident in which one or more prospective or serving corps members were kidnapped, killed, sexually assaulted, physically assaulted or robbed, as reported in Nigerian national news outlets from 1 January 2010 to 31 December 2026. Road crashes are recorded as a separate harm type because they are the main documented reason for the night-travel ban [S07]. Coding rules, including the lifecycle stage, are in `docs/coding_protocol.md`.

Search procedure: keyword searches of the archives of Premium Times, Punch, Vanguard, The Guardian (Nigeria), Daily Trust, Channels Television, The Cable and Sahara Reporters were planned, using combinations of "corps member", "corper", "NYSC" with "kidnapped", "abducted", "killed", "attacked", "raped", "robbed". The searches run by `nysc_safety.news_search` (17 phrases per outlet, through each outlet's WordPress search interface) are logged with date, outlet, query, HTTP status and number of results in `data/interim/news_search_log.csv`; two Daily Trust queries interrupted by a dropped connection were rerun on 5 October 2026 and are logged in `data/interim/news_search_rerun_log.csv`.

The full archive search succeeded for Premium Times, Daily Trust and Channels Television (6,364 distinct articles). Punch, Vanguard, The Guardian (Nigeria) and The Cable refused automated requests (HTTP 403 or a bot-check page), and Sahara Reporters has no comparable search interface. Articles from these five outlets enter the register only through targeted web searches for specific incidents, so they confirm incidents but do not give a complete count of coverage.

Screening: headlines in the article index that mention corps members (or NYSC) and a harm term were screened by hand (`data/interim/screening/headline_screening.csv`), grouped into candidate incidents (`candidates_kidnapping.csv`, `candidates_other.csv`) and verified against the article text. Every decision to include, exclude, merge or hold a candidate is recorded with its reason in `data/interim/screening/screening_decisions.csv`.

Coding is AI-assisted: Claude (Anthropic) screens and codes articles under `docs/coding_protocol.md`, with one coder. Every row lists the article URLs used and a coding note explaining the lifecycle stage and harm type assigned, so that each coding decision can be checked against its sources.

## 5. Phase 3: risk analysis

Salience gap (H1): articles per incident by geopolitical zone, and the correlation between state shares of incidents and state shares of articles.

Travel window (H2): share of incidents within 7 days of official camp-opening and passing-out dates, compared with the share of calendar days those windows cover. Official dates come from NYSC mobilisation timetables reported for each batch, collected in `data/interim/calendar/nysc_dates.csv` (one row per reported date, with the chosen date marked and superseded or implausible dates kept with a reason) and built into `data/processed/nysc_calendar.csv` by `nysc_safety.camp_calendar` [A11]. For 2010 to 2015 and several later streams, the only sources found are job and education sites that reproduce NYSC timetables, rated Low in the source log; the H2 test is repeated with reported dates only, and with 2016 to 2026 only.

Exposure-adjusted rates (H3): incidents per 10,000 corps members sworn in, by state and period, with exact Poisson confidence intervals [A02]. No published series gives corps members sworn in by state and year, so exposure is modelled (`nysc_safety.exposure`): each state's share is its median reported orientation-course size (208 figures from news reports and official statements, at least 3 per state, in `data/interim/exposure/state_course_figures.csv`) divided by the sum across states, multiplied by the national total for the year (`data/interim/exposure/national_totals.csv`; National Bureau of Statistics series for 2010 to 2014, Director-General statements for 2016, 2017, 2023 and 2025, interpolated between) [A09, A10]. Few course figures predate 2016, so the shares mainly reflect camp sizes from 2016 onwards.

Comparison with general kidnapping (H4): state-level rank correlation between corps member incident rates and general kidnapping rates per 100,000 population. Two comparison series are used. The first is Nigeria Watch [S09]. The second is a news-based series of general kidnapping reports, coded with the same procedure and outlets as the NYSC register so that the two series share the same reporting biases.

## 6. Data sources for the general kidnapping comparison

ACLED is not used, because its data access terms require an organisational account. Nigeria Watch was considered as the main replacement [S09]. Its methodology states that the database only counts fatalities, and kidnapping is not one of its coded causes [S10]. A text search for "kidnapped" returned 1,258 events, each with at least one death [S10]. Nigeria Watch therefore covers kidnappings in which someone died, not kidnappings in general.

The comparison uses two series:

- The main series is general kidnapping reports from the same outlets, coded with the same procedure as the NYSC register, so that both series share the same reporting biases. This series is used for the H4 decision rule in `docs/preregistration.md`.
- Nigeria Watch is a secondary series covering kidnapping events with at least one death, identified by text search and exported from the public interface [S10]. It is compared with the subset of NYSC incidents in which a corps member died.

The Council on Foreign Relations Nigeria Security Tracker is used as a historical cross-check for the years it covers. The change from ACLED is reported as a limitation.

Nigeria Watch also lists fatal events involving corps members (search terms "corper" and "NYSC" [S10]). These events are used as a cross-check on the completeness of the NYSC incident register for incidents with deaths.

## 7. Phase 4: budget audit, 2018 to 2026

NYSC allocations are taken from the Federal Government appropriation acts for 2018 to 2026. Line items related to security, camps, transport and insurance are identified by their descriptions. Values are converted to constant 2024 naira with the National Bureau of Statistics consumer price index and divided by the number of corps members mobilised in each year.

## 8. Outputs

- README with method and findings
- Policy brief for the Federal Ministry of Youth Development, the NYSC Directorate and the National Assembly committees on youth
- Streamlit dashboard of incidents, rates and the scorecard
- Public write-up

## 9. Limitations

- The NYSC calendar for 2010 to 2015 rests mainly on job and education sites that reproduce official timetables, and some streams have no recorded camp dates. Missing dates are derived [A11], which can shift the travel windows by a few days.
- Four of the eight planned outlets (Punch, Vanguard, The Guardian (Nigeria), The Cable) could not be searched systematically, and Sahara Reporters has no archive search interface. Incidents reported only in these outlets are found only through targeted web searches and may be missed.
- News coverage is incomplete and uneven. Incidents in rural northern states, and incidents in which victims were released quickly, are less likely to be reported. The salience analysis (H1) measures this bias where it can, but unreported incidents cannot be counted.
- Swearing-in figures are reported inconsistently across states and batches; rates depend on the exposure assumption [A02].
- Nigeria Watch records only events with deaths [S10], and the coded news series depends on the same outlets as the NYSC register. Neither is equivalent to ACLED in coverage or method.
- The policy audit covers published rules. Practice in individual states, and internal circulars not made public, are outside its reach. No survey of corps members and no freedom of information requests are used.
- The 2026 reform is assessed as announced. Its legal text was not available as of 5 October 2026 [S06].

## 10. Ethics and data protection

The Nigeria Data Protection Act 2023 applies. Victim names are not stored in the repository. Incidents are identified by anonymous IDs and located at local government area level at the finest.

## 11. Deviations from the pre-registration

The pre-registration (git tag `prereg-v1`) defines articles per incident as the number of distinct articles in the eight searched outlets within 30 days of the event. Only three outlets could be searched in full (section 4). To keep the measure comparable across incidents, `n_articles` counts distinct articles in Premium Times, Daily Trust and Channels Television, found by the logged archive search, within 30 days of the event date. Articles found through targeted web searches are listed in `source_ids` but are not counted in `n_articles`. The same three outlets define the coded news series of general kidnapping used for H4.

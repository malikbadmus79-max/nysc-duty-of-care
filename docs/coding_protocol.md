# Coding protocol for the incident register

Rules for building `data/processed/incidents.csv` from news reports. Category lists match `nysc_safety.coding`, and `nysc_safety.coding.validate_register` checks every row against them.

## 1. Inclusion

An incident is included when all of the following hold:

- At least one person harmed is a prospective corps member (holding a call-up letter and not yet sworn in) or a serving corps member.
- The harm is a kidnapping, killing, sexual assault, physical assault, robbery or road crash, or another harm listed under `other`.
- The event took place in Nigeria between 1 January 2010 and 31 December 2026.
- At least one article in a searched outlet reports the event.

Excluded: harms to NYSC staff who are not corps members, harms to former corps members after the end of service, deaths from illness with no external cause, and suicides. Excluded reports are kept in `data/interim/news_screening.csv` with the exclusion reason.

## 2. Unit of record

One incident is one event: one attack, abduction or crash, at one place, on one day. Several corps members harmed in the same event form one incident, with the number recorded in `victims_total`. Several articles about one event are linked to one incident ID. Two abductions on the same road on the same day by apparently different groups are recorded as two incidents if the reports describe them as separate.

## 3. Variables

| Variable | Values | Rule |
|----------|--------|------|
| `incident_id` | `INC0001`, `INC0002`, ... | Assigned in order of event date. |
| `event_date` | ISO date | Day the harm began [A01]. |
| `date_precision` | `day`, `month`, `year` | Precision of `event_date`. |
| `state` | 36 states and `FCT` | State where the harm began. |
| `lga` | Local government area name, or empty | Finest location kept. No town, street or institution names. |
| `lifecycle_stage` | See section 4 | Stage of the service year when the harm began. |
| `harm_type` | `kidnapping`, `killing`, `sexual_violence`, `physical_assault`, `robbery`, `road_crash`, `other` | Most serious harm in the incident, in the order listed. |
| `member_status` | `prospective`, `serving`, `mixed`, `unknown` | Status of the corps members harmed. |
| `victims_total` | Whole number or empty | Corps members harmed. Other victims are not counted here. |
| `victims_killed` | Whole number or empty | Corps members killed. |
| `victims_abducted` | Whole number or empty | Corps members abducted. |
| `outcome` | `released`, `rescued`, `killed_in_captivity`, `escaped`, `still_held`, `unknown`, `not_applicable` | Outcome for abducted corps members, as last reported. |
| `ransom_reported` | `yes`, `no`, `unknown` | Whether a ransom demand or payment is reported. |
| `perpetrator_type` | `armed_group`, `bandits`, `cult`, `robbers`, `community`, `state_actor`, `unknown` | As named in the report; `unknown` when the report does not attribute the attack. |
| `n_articles` | Whole number | Distinct articles in the searched outlets within 30 days of the event. |
| `source_ids` | `S10;S11` | Source log IDs of all articles used. |
| `coding_note` | Short text | One or two sentences giving the reason for the lifecycle stage and harm type assigned, with no names. |

Victim names, ages, institutions and photographs are not recorded.

## 4. Lifecycle stages

| Code | Stage | Rule |
|------|-------|------|
| `travel_to_camp` | Travel to orientation camp | Prospective corps member on the way to camp, from the home base to the camp gate [A04]. |
| `camp` | Orientation camp | Inside camp, or in the camp's immediate surroundings during the orientation course. |
| `travel_to_ppa` | Travel to place of primary assignment | Corps member on the way from camp to the posting, or on relocation to a new state after redeployment [A04]. |
| `ppa` | Place of primary assignment | At the place of work, at lodging provided by the employer or community, or within the host community during the service year. |
| `cds` | Community development service | During a community development service activity or meeting. |
| `personal_travel` | Personal travel | Travel during the service year with no stated link to service duties [A04]. |
| `passing_out` | Passing out | At the passing-out venue, or on the journey home within 14 days after passing out. |
| `unknown` | Unknown | The report does not allow a stage to be assigned. |

## 5. Coding and checking

Coding is AI-assisted: Claude (Anthropic) screens articles, applies the rules above and writes the coding note for each row, with one coder. Before analysis, every row is checked with `nysc_safety.coding.validate_register`, and the coding note for each row is reread against the cited articles. Rows changed at this stage are listed in `data/interim/coding_changes.csv` with the old value, the new value and the reason.

## 6. Change log

| Date | Change |
|------|--------|
| 2026-10-05 | First version. |
| 2026-10-05 | Coding defined as AI-assisted with one coder; pre-analysis check of every row. `coding_note` column added. |
| 2026-10-05 | Journeys leaving camp coded `travel_to_ppa` [A05]; election duty coded `ppa` [A06]. |
| 2026-10-05 | Weekday-only dates resolved by publication date [A07]; duty-linked return journeys to the posting coded `ppa` [A08]. Incidents at separate locations on the same day are recorded separately even when one report covers both. |

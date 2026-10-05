# Policy audit and duty-of-care scorecard

Assessment of NYSC rules against the duty-of-care obligations and security risk management elements published by the Global Interagency Security Forum (GISF) [S01, S02]. Status as of 5 October 2026: criteria and scoring rules fixed; the NYSC Act and the 1974 Bye-laws reviewed in full; revised Bye-laws and redeployment rules not yet obtained; no scores assigned.

## 1. Reference standard

GISF guidance was written for humanitarian organisations, which, like the NYSC, send people into insecure areas under organisational direction. S01 sets out six duty-of-care obligations: know the risks, establish mitigation measures, develop emergency plans, ensure informed consent, raise awareness, and provide appropriate support. It also lists ten elements of a security risk management framework. S02 reviews the 2015 Oslo District Court ruling in Dennis v Norwegian Refugee Council, in which an employer was found grossly negligent over the kidnapping of staff, and draws out the court's emphasis on context and risk analysis, adherence to security plans, informing staff of increased risk, and documentation.

The NYSC differs from an employer in two ways that raise the standard of care: failing to report for service is an offence (section 13), and the Directorate, not the corps member, assigns the state of service (section 4) [S03]. S01 notes that an organisation's responsibility rises with the control it has over a person's work environment and tasks and with the information it holds on the risks (page 8). The Directorate controls both the state of service and the place of primary assignment [S03, section 9(1)]. Informed consent (D4) is therefore assessed as the provision of risk information and the availability of risk-based redeployment, since refusal of service is not an option.

## 2. Criteria

| ID | Criterion | Basis in S01 and S02 |
|----|-----------|----------------------|
| D1 | Governance and accountability for corps member safety | S01 governance and accountability; security policy |
| D2 | Risk assessment of states, routes and places of primary assignment | S01 know the risks; risk assessment. S02 context and risk analysis |
| D3 | Risk-informed deployment, redeployment and exemption | S01 establish mitigation measures. S02 identify and implement mitigating measures |
| D4 | Informed consent and pre-deployment risk information | S01 ensure informed consent. S02 informing staff of increased risk |
| D5 | Travel management for camp, posting and passing-out journeys | S01 travel management and support |
| D6 | Security at orientation camps | S01 security plans |
| D7 | Security at places of primary assignment and during community development service | S01 security plans |
| D8 | Security awareness and training | S01 raise awareness; awareness and capacity building |
| D9 | Incident reporting and recording | S01 incident monitoring and reporting |
| D10 | Crisis management and kidnap response | S01 develop emergency plans; crisis management. S02 crisis management planning and response |
| D11 | Post-incident support, insurance and compensation | S01 provide appropriate support. S02 redress measures |
| D12 | Review, learning and public reporting | S01 compliance and effectiveness monitoring. S02 follow-up and review |

## 3. Scoring scale

| Score | Meaning |
|-------|---------|
| 0 | No provision found |
| 1 | Provision stated in general terms, with no procedure or responsible office |
| 2 | Provision with a procedure or a responsible office, but not both, or not applied to all stages of the service year |
| 3 | Provision with a procedure and a responsible office, covering all stages of the service year |

Each criterion is scored separately for two frameworks: `current` (rules in force before the June 2026 reform) and `reform_2026` (the reform package as announced [S04, S05]). A provision counts only if it is in a published document. Statements by officials count when they are directives to corps members or staff, not when they describe intentions. Scores, with the evidence IDs that support them, are recorded in `data/processed/policy_scorecard.csv` and checked by `nysc_safety.scorecard.validate_scores`.

## 4. Documents

| Document | Framework | Status at 5 October 2026 | Source |
|----------|-----------|--------------------------|--------|
| NYSC Act, Cap. N84, Laws of the Federation of Nigeria 2004 | current | Reviewed in full | S03 |
| NYSC Bye-laws 1974 (L.N. 37 of 1974), as printed in the 2004 Laws of the Federation | current | Reviewed in full | S03 |
| NYSC Bye-laws, later revised edition issued by the Directorate | current | Not yet obtained | |
| Directorate travel and security directives to corps members | current | Two directives obtained (2021, 2022) | S07, S08 |
| Redeployment and relocation rules and published grounds | current | Not yet obtained | |
| Federal Executive Council reform package | reform_2026 | News reports of the announcement obtained; official text not located | S04, S05 |
| Bill to amend the NYSC Act | reform_2026 | Not located; executive bill reported as in preparation in July 2026 | S06 |

## 5. Evidence collected

Evidence rows, with the wording of each provision, are kept in `data/interim/policy_evidence.csv` (25 rows, E01 to E25). Summary by criterion:

| Criterion | Current framework | Reform package (June 2026) |
|-----------|-------------------|----------------------------|
| D1 | Security of corps members is a duty of the Local Government Committee, chaired by the local government chairman (section 8(3)(d)). State governing boards provide welfare facilities and transport and deploy members within the state (section 6(2)). The Director-General has general responsibility for day-to-day running (section 5(2)). No national office is named as responsible for corps member safety [S03]. | Civilian operational leadership, with the military providing security support [S04, S05]. |
| D2 | No provision found. Placement considers qualifications, vacancies and national needs (section 9(4)); security risk is not listed [S03]. | No provision announced. |
| D3 | The Act directs assignment outside the state of origin as far as possible (section 1(4)(b)). The Directorate decides place and time of deployment and cannot be compelled to deploy a member to a particular project (section 9(1) and (5)). Exemption or deferment requires a Gazette order and National Defence and Security Council approval and names no security ground (section 17). Appeals go to the Presidency (section 20) [S03]. | Risk-sensitive deployment framework limiting exposure to security flashpoints, especially for non-indigenes; technology-driven deployment [S04, S05]. |
| D4 | No provision found [S03]. | No provision announced. |
| D5 | Local Government Committees collect members from camp and return them for passing out (section 8(3)(b)); the journey from home to camp is not covered [S03]. Night-travel ban and shelter rules issued as Director-General directives in 2021 and 2022 [S07, S08]. Members need written consent to leave camp or station, on pain of losing their allowance (Bye-law 3 and Second Schedule) [S03]. | No change announced. |
| D6 | States provide orientation camps (section 7(4)); no security standard is set [S03]. | National grading and certification of camps covering safety, accommodation and healthcare [S05]. |
| D7 | Local Government Committee duty to ensure security, with a police representative on the Committee (section 8(2)(c) and 8(3)(d)); local governments and employers provide accommodation and transport (sections 8(4)(b) and 18(2)) [S03]. | No change announced. |
| D8 | Security advice in the Director-General's closing address at orientation [S08]. The 1974 code of conduct contains one safety rule, on crash helmets (Bye-law 3(1)(b)(vii)) [S03]. | No provision announced. |
| D9 | No incident reporting procedure. Grievances follow a chain from head of department to the Director, and airing a grievance in the news media is a disciplinary offence (Bye-law 10) [S03]. | No provision announced. |
| D10 | No provision found [S03]. | No provision announced. |
| D11 | Medical care at military or government facilities, with discretionary refund of private treatment (Bye-laws 4 and 5); no insurance or compensation provision [S03]. | No provision announced. |
| D12 | Annual report to the Presidency, laid before the National Defence and Security Council (section 15(3) and (4)); no requirement to report harm to corps members [S03]. | Amendment of the NYSC Act directed [S04, S06]. |

"No provision found" refers to the documents reviewed so far, listed in section 4.

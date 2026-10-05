# Policy audit and duty-of-care scorecard

Assessment of NYSC rules against the duty-of-care obligations and security risk management elements published by the Global Interagency Security Forum (GISF) [S01, S02]. Status as of 5 October 2026: criteria and scoring rules fixed; evidence collection under way; no scores assigned.

## 1. Reference standard

GISF guidance was written for humanitarian organisations, which, like the NYSC, send people into insecure areas under organisational direction. S01 sets out six duty-of-care obligations: know the risks, establish mitigation measures, develop emergency plans, ensure informed consent, raise awareness, and provide appropriate support. It also lists ten elements of a security risk management framework. S02 reviews the 2015 Oslo District Court ruling in Dennis v Norwegian Refugee Council, in which an employer was found grossly negligent over the kidnapping of staff, and draws out the court's emphasis on context and risk analysis, adherence to security plans, informing staff of increased risk, and documentation.

The NYSC differs from an employer in two ways that raise the standard of care: failing to report for service is an offence (section 13), and the Directorate, not the corps member, assigns the state of service (section 4) [S03]. Informed consent (D4) is therefore assessed as the provision of risk information and the availability of risk-based redeployment, since refusal of service is not an option.

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
| NYSC Act, Cap. N84, Laws of the Federation of Nigeria 2004 | current | Obtained | S03 |
| NYSC Bye-laws, current revised edition | current | Not yet obtained | |
| Directorate travel and security directives to corps members | current | Two directives obtained (2021, 2022) | S07, S08 |
| Redeployment and relocation rules and published grounds | current | Not yet obtained | |
| Federal Executive Council reform package | reform_2026 | News reports of the announcement obtained; official text not located | S04, S05 |
| Bill to amend the NYSC Act | reform_2026 | Not located; executive bill reported as in preparation in July 2026 | S06 |

## 5. Evidence collected

Evidence rows are kept in `data/interim/policy_evidence.csv`. Summary of the first 13 rows:

| Criterion | Current framework | Reform package (June 2026) |
|-----------|-------------------|----------------------------|
| D1 | The Act places the security of corps members with Local Government Committees (section 8) and gives State Governing Boards responsibility for accommodation, transport and deployment within states (section 6) [S03]. No national office with responsibility for corps member security is named in the Act. | Civilian operational leadership, with the military providing security support [S04, S05]. |
| D2 | No provision found in the Act. | No provision announced. |
| D3 | Exemption, deferment and adjustment of the service period at the Directorate's discretion (section 17) [S03]. | Risk-sensitive deployment framework limiting exposure to security flashpoints, especially for non-indigenes; technology-driven deployment [S04, S05]. |
| D4 | No provision found in the Act. | No provision announced. |
| D5 | Ban on night travel, shelter at military barracks or designated places after 6:00 pm, and use of recognised motor parks, issued as Director-General directives in 2021 and 2022 [S07, S08]. Transport within states arranged by State Governing Boards (section 6) [S03]. | No change announced. |
| D6 | No provision found in the Act. | National grading and certification of camps covering safety, accommodation and healthcare [S05]. |
| D7 | Employer duties on accommodation, welfare and medical services (section 18) and Local Government Committee duty on security (section 8) [S03]. | No change announced. |
| D8 | Security advice given in the Director-General's address at the close of orientation [S08]. | No provision announced. |
| D9 | No provision found in the Act. | No provision announced. |
| D10 | No provision found in the Act. | No provision announced. |
| D11 | No provision found in the Act. | No provision announced. |
| D12 | No provision found in the Act. | Amendment of the NYSC Act directed [S04, S06]. |

"No provision found" in this table refers to the documents obtained so far, listed in section 4.

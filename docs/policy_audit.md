# Policy audit and duty-of-care scorecard

Assessment of NYSC rules against the duty-of-care obligations and security risk management elements published by the Global Interagency Security Forum (GISF) [S01, S02]. Status as of 5 October 2026: the NYSC Act, the 1974 Bye-laws and the revised 2011 Bye-laws reviewed in full; first-round scores assigned by one coder; second independent scoring not yet done.

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

Each criterion is scored separately for two frameworks. `current` covers the rules and practice in force before the June 2026 reform. `reform_2026` covers the same rules plus the reform package as announced by the Federal Ministry of Youth Development [S21]; a criterion the reform does not address keeps its `current` score. Scores, with the evidence IDs that support them, are recorded in `data/processed/policy_scorecard.csv` and checked by `nysc_safety.scorecard.validate_scores`.

Evidence rules:

- Statutes, Bye-laws and published directives to corps members or staff count as provisions.
- Decisions reported by officials (for example, ceasing to post corps members to named areas) count as practice. Practice without a published procedure or a named responsible office scores at most 1.
- Statements of intention, such as a promise to review protocols, do not raise a score.
- An office counts as responsible only if a published document assigns it the task.

## 4. Documents

| Document | Framework | Status at 5 October 2026 | Source |
|----------|-----------|--------------------------|--------|
| NYSC Act, Cap. N84, Laws of the Federation of Nigeria 2004 | current | Reviewed in full | S03 |
| NYSC Bye-laws 1974 (L.N. 37 of 1974), as printed in the 2004 Laws of the Federation | current | Reviewed in full | S03 |
| NYSC Bye-laws (Revised 2011), published by the NYSC | current | Reviewed in full | S11 |
| Directorate travel and security directives to corps members | current | Two directives obtained (2021, 2022) | S07, S08 |
| Statements on insurance, posting decisions and safety guidance | current | Obtained (2021 to 2026) | S12 to S17 |
| Relocation rules | current | No published grounds for relocation found; the 2011 Bye-laws set the channel for requests (paragraph 12) | S11 |
| Federal Executive Council reform package | reform_2026 | Official statement obtained | S21 |
| Bill to amend the NYSC Act | reform_2026 | Not located; executive bill reported as in preparation in July 2026 | S06 |

## 5. Evidence collected

Evidence rows, with the wording of each provision, are kept in `data/interim/policy_evidence.csv` (42 rows, E01 to E42). The main findings by criterion are in the rationale column of section 6.

Three findings stand outside the scores. First, both editions of the Bye-laws restrict corps members' movement and speech: travel outside the state of service needs written permission (2011 Bye-laws, paragraph 3(26)), addressing the press on policy is an offence (paragraph 3(18)), and the 1974 edition penalised airing grievances in the news media (Bye-law 10(2)) [S03, S11]. These rules limit self-protection and public reporting without a matching duty on the Directorate. Second, refusing a posting is penalised, and no rule allows refusal or relocation on security grounds (2011 Bye-laws, paragraphs 3(20) and 12) [S11]. Third, on 26 August 2026, after the reform was approved, 16 corps members travelling from the Bayelsa orientation camp were abducted in Kogi State [S18, S19, C02]. The Act provides for collecting corps members from camp within the state of service (section 8(3)(b), E09) but does not cover journeys between states, which is where this abduction took place.

## 6. Scores

First-round scores, assigned on 5 October 2026 by one coder (`coder_1`).

| ID | Criterion | Current | Reform 2026 | Rationale (current; change under reform) | Sources |
|----|-----------|---------|-------------|------------------------------------------|---------|
| D1 | Governance and accountability | 2 | 2 | The Act names an office for corps member security, the Local Government Committee (section 8(3)(d)), but sets no procedure and limits the duty to members deployed to the local government area; no national office is named. Reform: civilian operational leadership with military security support is announced, but no office responsible for corps member safety is named; score unchanged. | S03, S04, S05, S21 |
| D2 | Risk assessment | 0 | 1 | No published risk assessment of states, routes or places of primary assignment; placement criteria in section 9(4) do not include security. Reform: risk-sensitive deployment implies risk assessment and is stated as national policy, but no method, data source or responsible office is announced. | S03, S21 |
| D3 | Risk-informed deployment | 1 | 1 | States and LGAs have been excluded from postings in practice, but no criteria, procedure or responsible office are published; exemption names no security ground, refusing a posting is penalised and relocation requests have no stated grounds. Reform: risk-sensitive deployment is stated as national policy for the first time; no criteria, procedure or responsible office are announced, so the score is unchanged. | S03, S04, S05, S11, S14, S15, S16, S21 |
| D4 | Informed consent | 0 | 0 | No provision for risk information or consent; the pledge commits members to serve wherever deployed. | S11 |
| D5 | Travel management | 2 | 2 | Local Government Committees collect members from camp and return them for passing out within the state of service (an office with a defined task), and the Director-General has issued travel directives; journeys between states, to camp and from camp, are not covered by any procedure. | S03, S07, S08, S11, S15 |
| D6 | Camp security | 1 | 2 | States provide camps and the Bye-laws restrict what members bring into camp, but no camp security standard or responsible office exists. Reform: a national grading and certification system for camps, covering safety, is a procedure; the certifying office is not named. | S03, S04, S05, S11, S16, S21 |
| D7 | Security at place of assignment | 2 | 2 | The Local Government Committee, which includes a police representative, has a duty to ensure security at the place of primary assignment; no procedure is set. | S03 |
| D8 | Awareness and training | 1 | 1 | Security advice is given in addresses and one safety rule appears in the Bye-laws; no training curriculum is published and the 2021 safety guidance was not adopted. | S03, S08, S17 |
| D9 | Incident reporting | 0 | 0 | No incident reporting procedure; airing grievances in the media and addressing the press on policy are disciplinary offences. | S03, S11 |
| D10 | Crisis and kidnap response | 0 | 0 | No published crisis management or kidnap response plan; response in the 2026 Kogi abduction relied on security agencies. | S18, S19 |
| D11 | Support, insurance, compensation | 2 | 2 | Health and life insurance from call-up and an insurance office at headquarters; insurer, cover limits and claim procedure are not published, and no provision for psychosocial or other post-incident support is published. | S03, S11, S12, S13 |
| D12 | Review and reporting | 1 | 1 | The Directorate reports annually but is not required to report harm to corps members; the post-incident review announced in 2026 has no published terms. Reform: amendment of the NYSC Act is directed; no safety review or reporting duty is announced. | S03, S04, S06, S19 |
| | Total (of 36) | 12 (33.3%) | 14 (38.9%) | | |

The current framework scores 12 of 36 (33.3%). The reform package as announced raises this to 14 of 36 (38.9%), through risk-sensitive deployment stated as national policy (D2) and the certification of camps (D6). Three criteria score 0 under both frameworks: informed consent (D4), incident reporting (D9) and crisis and kidnap response (D10). No criterion scores 3.

## 7. Limitations of the scores

- Scores are from one coder. A second coder will score the same evidence independently, and agreement will be reported with quadratic-weighted Cohen's kappa (`nysc_safety.reliability.weighted_kappa`) before the scores are used in any output.
- Internal circulars, security plans and insurance contracts that are not published cannot be scored. A score of 0 means no published provision was found, not that no practice exists.
- The reform is scored as announced [S21]. Its legal text was not available as of 5 October 2026 [S06].

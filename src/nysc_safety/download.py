"""Download the primary documents listed in the source log to data/raw/pdfs/.

Documents are PDFs, except budget documents published only as Excel workbooks
(`.xlsx`); each file is checked against the signature of its type.

Run from the repository root with `python -m nysc_safety.download`.
Existing files are not overwritten, in line with the rule that raw files
are never changed after download.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import requests

from nysc_safety import paths

USER_AGENT = "nysc-duty-of-care research project (github.com/malikbadmus79-max)"
DELAY_SECONDS = 2.0
PDF_DIR: Path = paths.DATA_RAW / "pdfs"
SIGNATURES: dict[str, bytes] = {".pdf": b"%PDF", ".xlsx": b"PK\x03\x04"}
"""First bytes expected for each file type."""
BUDGET_OFFICE = "https://budgetoffice.gov.ng/index.php"


@dataclass(frozen=True)
class Document:
    """A primary document with its source log ID."""

    source_id: str
    filename: str
    url: str


DOCUMENTS: tuple[Document, ...] = (
    Document(
        "S01",
        "S01_gisf_security_risk_management_basic_guide_2017.pdf",
        "https://gisf.ngo/wp-content/uploads/2020/12/Security-Risk-Management-A-basic-guide-for-smaller-NGOs.pdf",
    ),
    Document(
        "S02",
        "S02_gisf_dennis_v_nrc_review_2016.pdf",
        "https://gisf.ngo/wp-content/uploads/2016/09/Duty-of-Care-A-review-of-the-Dennis-v-Norwegian-Refugee-Council-ruling.pdf",
    ),
    Document(
        "S03",
        "S03_nysc_act_cap_n84_lfn_2004.pdf",
        "https://placng.org/lawsofnigeria/laws/NATIONAL%20YOUTH%20SERVICE%20CORPS%20ACT.pdf",
    ),
    Document(
        "S551",
        "S551_npc_population_projections_2022.pdf",
        "https://s3-eu-west-1.amazonaws.com/cfa-openafrica/resources/ebe9dbbb-43de-42dd-8733-297aac5fda15/"
        "national-population-commission-projection_2022.pdf",
    ),
    Document(
        "S552",
        "S552_nbs_population_forecasts_2016.pdf",
        "https://s3-eu-west-1.amazonaws.com/cfa-openafrica/resources/091db6c5-fdb4-4bce-bdd1-36790ff5269b/"
        "population-forecasts.pdf",
    ),
    Document("S556", "S556_approved_budget_details_2018.pdf",
             f"{BUDGET_OFFICE}/resources/internal-resources/budget-documents/2018-approved-budget-details/download"),
    Document("S557", "S557_budget_as_passed_2019.pdf",
             f"{BUDGET_OFFICE}/resources/internal-resources/budget-documents/2019-budget/download"),
    Document("S558", "S558_appropriation_repeal_and_enactment_act_2020.pdf",
             f"{BUDGET_OFFICE}/resources/internal-resources/budget-documents/appropriation-repeal-and-enactment-act-2020/download"),
    Document("S559", "S559_revised_appropriation_details_2020.pdf",
             f"{BUDGET_OFFICE}/resources/internal-resources/budget-documents/revised-2020-appropriation/download"),
    Document("S560", "S560_appropriation_act_2021.xlsx",
             f"{BUDGET_OFFICE}/resources/internal-resources/budget-documents/2021-appropriation-act/download"),
    Document("S561", "S561_appropriation_act_2022.pdf",
             f"{BUDGET_OFFICE}/resources/internal-resources/budget-documents/2022-appropriation-act/download"),
    Document("S562", "S562_appropriation_act_2023_youth_and_sports.pdf",
             f"{BUDGET_OFFICE}/2023-appropriation-act-by-sector/federal-ministry-of-youth-sports-development-2/download"),
    Document("S563", "S563_appropriation_act_2024.pdf", f"{BUDGET_OFFICE}/2024-appropriation-act/2024-appropriation-act/download"),
    Document("S564", "S564_appropriation_act_2025.pdf", f"{BUDGET_OFFICE}/2025-appropriation-act/2025-appropriation-act/download"),
    Document("S565", "S565_appropriation_act_details_2026.pdf",
             f"{BUDGET_OFFICE}/2026-appropriation-act-details/2026-appropriation-act-details-pdf/download"),
)


def download(document: Document, folder: Path = PDF_DIR, timeout: int = 180) -> Path:
    """Download one document unless the file already exists; return its path.

    The file is streamed to a `.part` file and renamed only when complete, so an
    interrupted download never leaves a partial file under the final name.
    """
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / document.filename
    if target.exists():
        return target
    partial = target.with_name(target.name + ".part")
    headers = {"User-Agent": USER_AGENT}
    with requests.get(document.url, headers=headers, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        received = 0
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=256 * 1024):
                handle.write(chunk)
                received += len(chunk)
                if total:
                    print(f"\r{document.source_id}: {received / total:6.1%} of {total:,} bytes", end="", flush=True)
        if total:
            print()
    signature = SIGNATURES[target.suffix.lower()]
    with partial.open("rb") as handle:
        matches = handle.read(len(signature)) == signature
    if not matches:
        partial.unlink()
        raise ValueError(f"{document.url} did not return a {target.suffix} file")
    partial.replace(target)
    return target


def main() -> None:
    """Download every document in DOCUMENTS, pausing between requests."""
    for index, document in enumerate(DOCUMENTS):
        if index:
            time.sleep(DELAY_SECONDS)
        path = download(document)
        print(f"{document.source_id}: {path.name} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

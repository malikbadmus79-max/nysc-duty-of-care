"""Download the primary documents listed in the source log to data/raw/pdfs/.

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
)


def download(document: Document, folder: Path = PDF_DIR, timeout: int = 60) -> Path:
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
    with partial.open("rb") as handle:
        if handle.read(4) != b"%PDF":
            partial.unlink()
            raise ValueError(f"{document.url} did not return a PDF")
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

from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from utils import filename_likely_in_range


SUPPORTED_EXTENSIONS = {".zip", ".csv", ".xlsx", ".xls"}


def build_requests_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "nemweb-etl-pipeline/1.0 (+https://www.nemweb.com.au/)",
        }
    )
    return session


def discover_dataset_links(
    directory_urls: list[str],
    file_name_pattern: str,
    start_dt,
    end_dt,
    logger,
) -> list[str]:
    """Scan NEMWeb directory listings and return matching file links."""
    session = build_requests_session()
    discovered_links: list[str] = []
    seen_links: set[str] = set()
    pattern_upper = file_name_pattern.upper()

    for directory_url in directory_urls:
        logger.info("Scanning directory page: %s", directory_url)
        response = session.get(directory_url, timeout=60)
        response.raise_for_status()
        logger.info("Directory response for %s returned HTTP %s", directory_url, response.status_code)

        soup = BeautifulSoup(response.text, "html.parser")
        hrefs: list[str] = [anchor["href"].strip() for anchor in soup.find_all("a", href=True)]

        # Fallback for odd NEMWeb pages where anchor parsing is unreliable.
        if not hrefs:
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', response.text, flags=re.IGNORECASE)

        logger.info("Found %s href entries in %s", len(hrefs), directory_url)
        preview_hrefs = hrefs[:10]
        if preview_hrefs:
            logger.info("Sample hrefs from %s: %s", directory_url, ", ".join(preview_hrefs))

        for href in hrefs:
            file_name = Path(href).name
            file_name_upper = file_name.upper()
            suffix = Path(file_name).suffix.lower()

            if pattern_upper not in file_name_upper:
                continue
            if suffix not in SUPPORTED_EXTENSIONS:
                continue
            if not filename_likely_in_range(file_name, start_dt, end_dt):
                logger.info("Skipping %s because it falls outside the requested filename date range", file_name)
                continue

            file_url = urljoin(directory_url, href)
            if file_url in seen_links:
                continue

            seen_links.add(file_url)
            discovered_links.append(file_url)
            if len(discovered_links) <= 10:
                logger.info("Matched file link: %s", file_url)

    logger.info("Detected %s candidate files for pattern %s", len(discovered_links), file_name_pattern)
    return discovered_links


def download_file(url: str, download_dir: Path, logger) -> Path:
    """Download a remote file into a temporary working directory."""
    session = build_requests_session()
    response = session.get(url, timeout=120, stream=True)
    response.raise_for_status()

    file_path = download_dir / Path(url).name
    with file_path.open("wb") as output_handle:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                output_handle.write(chunk)

    logger.info("Downloaded file: %s", file_path.name)
    return file_path


def _extract_zip_file(zip_path: Path, working_dir: Path, logger, extracted_files: List[Path]) -> None:
    with zipfile.ZipFile(zip_path, "r") as zip_file:
        member_names = zip_file.namelist()
        zip_file.extractall(working_dir)
        logger.info("Extracted ZIP file %s with %s members", zip_path.name, len(member_names))

    for member_name in member_names:
        extracted_path = working_dir / member_name
        if extracted_path.is_dir():
            continue
        suffix = extracted_path.suffix.lower()
        if suffix == ".zip":
            _extract_zip_file(extracted_path, extracted_path.parent, logger, extracted_files)
        elif suffix in {".csv", ".xlsx", ".xls"}:
            extracted_files.append(extracted_path)


def prepare_dataset_files(file_links: list[str], logger) -> list[Path]:
    """
    Download and unpack all candidate files into a temporary folder.
    Returned files are ready for parsing and should be used only within the temp folder lifetime.
    """
    if not file_links:
        return []

    temp_dir = Path(tempfile.mkdtemp(prefix="nemweb_"))
    logger.info("Created temporary working folder: %s", temp_dir)

    extracted_files: list[Path] = []
    for file_link in file_links:
        downloaded_file = download_file(file_link, temp_dir, logger)
        suffix = downloaded_file.suffix.lower()

        if suffix == ".zip":
            _extract_zip_file(downloaded_file, temp_dir, logger, extracted_files)
        elif suffix in {".csv", ".xlsx", ".xls"}:
            extracted_files.append(downloaded_file)

    return extracted_files


def cleanup_temp_files(file_paths: list[Path], logger) -> None:
    """Delete the temporary folder after processing."""
    if not file_paths:
        return

    temp_root = file_paths[0]
    while temp_root.parent != temp_root and not temp_root.name.startswith("nemweb_"):
        temp_root = temp_root.parent

    if temp_root.exists() and temp_root.name.startswith("nemweb_"):
        shutil.rmtree(temp_root, ignore_errors=True)
        logger.info("Deleted temporary working folder: %s", temp_root)

# ============================================================
# AquaInsight — BarentsWatch Historical Data Downloader
# Project: Aquaculture Data Intelligence Platform
# Target period: 2015–2025
# ============================================================

# 1. IMPORT LIBRARIES

import os
import csv
import io
import requests

from datetime import date
from pathlib import Path
from dotenv import load_dotenv


# ============================================================
# 2. LOAD API CREDENTIALS
# ============================================================

# Find project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load credentials from .env
load_dotenv(PROJECT_ROOT / ".env")

# Read credentials
CLIENT_ID = os.getenv("BARENTSWATCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("BARENTSWATCH_CLIENT_SECRET")

# Check credentials
if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Missing BarentsWatch API credentials")


# ============================================================
# 3. API CONFIGURATION
# ============================================================

TOKEN_URL = "https://id.barentswatch.no/connect/token"

DOWNLOAD_URL = (
    "https://www.barentswatch.no/bwapi/v1/geodata/"
    "download/fishhealth"
)

START_YEAR = 2015
END_YEAR = 2025

# Directory for downloaded files
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


# ============================================================
# 4. AUTHENTICATION FUNCTION
# ============================================================

def get_access_token():
    """Authenticate with BarentsWatch."""

    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "api"
    }

    response = requests.post(
        TOKEN_URL,
        data=payload,
        timeout=30
    )

    response.raise_for_status()

    token_data = response.json()

    return token_data["access_token"]


# ============================================================
# 5. CREATE DOWNLOAD PARAMETERS
# ============================================================

def create_download_params(year):
    """Generate API parameters for one reporting year."""

    # Determine the final ISO week of the year
    last_week = date(year, 12, 28).isocalendar().week

    params = {
        "filetype": "csv",
        "reporttype": "lice",
        "fromyear": year,
        "fromweek": 1,
        "toyear": year,
        "toweek": last_week
    }

    return params


# ============================================================
# 6. DOWNLOAD DATA
# ============================================================

def download_fishhealth(year, token):
    """Download raw sea-lice observations for one year."""

    # Prepare download parameters
    params = create_download_params(year)

    # Prepare authentication header
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Prepare output directory
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Prepare filename
    output_file = RAW_DATA_DIR / f"barentswatch_lice_{year}.csv"

    # Avoid accidentally overwriting existing raw data
    if output_file.exists():
        raise FileExistsError(
            f"File already exists: {output_file}"
        )

    print(f"\nDownloading sea-lice data for {year}...")

    # Send HTTP GET request
    response = requests.get(
        DOWNLOAD_URL,
        headers=headers,
        params=params,
        timeout=120
    )

    # Check HTTP response
    response.raise_for_status()

    # Check response content type
    content_type = response.headers.get(
        "Content-Type", ""
    ).lower()

    if "json" in content_type or "html" in content_type:
        raise ValueError(
            f"Expected CSV, received: {content_type}"
        )

    # Check that data was returned
    if not response.content:
        raise ValueError("API returned an empty response.")

    # Decode and inspect CSV before saving
    try:
        csv_text = response.content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Response is not valid UTF-8 CSV."
        ) from error

    first_line = csv_text.splitlines()[0] if csv_text.splitlines() else ""

    # Accept CSV files using comma or semicolon delimiters
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

    reader = csv.reader(
        io.StringIO(csv_text),
        delimiter=delimiter
    )

    header = next(reader, [])

    if len(header) < 2:
        raise ValueError(
            "Response does not contain a valid CSV header."
        )

    # Save original downloaded bytes
    output_file.write_bytes(response.content)

    print("Download successful!")
    print(f"Saved file: {output_file}")
    print(f"File size: {output_file.stat().st_size:,} bytes")
    print(f"CSV columns detected: {len(header)}")

    return output_file


# ============================================================
# 7. MAIN PROGRAM
# ============================================================

if __name__ == "__main__":

    print("=" * 50)
    print("AquaInsight — BarentsWatch Data Extraction")
    print("=" * 50)

    # Authenticate with BarentsWatch
    token = get_access_token()

    print("BarentsWatch authentication successful!")

    # Display project period
    print(f"Historical target: {START_YEAR}–{END_YEAR}")

    # Download the remaining historical years
for year in range(2016, 2026):

    print(f"\nProcessing year: {year}")

    downloaded_file = download_fishhealth(
        year,
        token
    )

print("\nHistorical data extraction completed.")

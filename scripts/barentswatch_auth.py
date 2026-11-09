import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Find the project's root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load credentials from the .env file
load_dotenv(PROJECT_ROOT / ".env")

# Read the API credentials
CLIENT_ID = os.getenv("BARENTSWATCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("BARENTSWATCH_CLIENT_SECRET")

# Check whether credentials were loaded
if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("BarentsWatch API credentials are missing.")

print("API credentials loaded successfully!")


# BarentsWatch authentication endpoint
TOKEN_URL = "https://id.barentswatch.no/connect/token"

# Information required for authentication
payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "api"
}

# Send authentication request
response = requests.post(
    TOKEN_URL,
    data=payload,
    timeout=30
)

# Check for HTTP errors
response.raise_for_status()

# Convert JSON response into a Python dictionary
token_data = response.json()

# Verify that we received a token
if "access_token" in token_data:
    print("BarentsWatch authentication successful!")
    print("Token expires in:", token_data.get("expires_in"), "seconds")
else:
    print("Authentication response did not contain an access token.")


# Retrieve sea-lice observations for one locality
API_URL = (
    "https://www.barentswatch.no/bwapi/v1/geodata/"
    "fishhealth/locality/15196/avgfemalelice/2025"
)

headers = {
    "Authorization": f"Bearer {token_data['access_token']}"
}

fish_response = requests.get(
    API_URL,
    headers=headers,
    timeout=30
)

fish_response.raise_for_status()

fish_data = fish_response.json()

print("\n=== SEA-LICE DATA ===")
observations = fish_data["data"]

print("Locality:", fish_data["localityNo"])
print("Year:", fish_data["year"])
print("Number of observations:", len(observations))
print("First observation:", observations[0])
print("Last observation:", observations[-1])

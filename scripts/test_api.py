"""Check that your AESO API key works by pulling 2 days of pool prices."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("AESO_API_KEY")
if not key:
    raise SystemExit("AESO_API_KEY is missing. Put it in your .env file.")

url = "https://apimgw.aeso.ca/public/poolprice-api/v1.1/price/poolPrice"
params = {"startDate": "2026-10-01", "endDate": "2026-10-02"}
resp = requests.get(url, params=params, headers={"API-KEY": key}, timeout=30)

print("Status:", resp.status_code)
if resp.status_code != 200:
    print(resp.text[:500])
    raise SystemExit("Request failed. See the message above.")

data = resp.json()
rows = data["return"]["Pool Price Report"]
print(f"Got {len(rows)} rows. First 3:")
for row in rows[:3]:
    print(row)
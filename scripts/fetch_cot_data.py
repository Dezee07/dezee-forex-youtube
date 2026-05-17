"""
Fetches the latest CFTC COT (Commitment of Traders) report for major forex pairs.
Outputs a JSON file with net positioning for commercials and large speculators.
"""

import requests
import json
import os
from datetime import datetime, timedelta

CFTC_URL = "https://publicreporting.cftc.gov/api/odata/v1/TriWeeklyCombined"

# CFTC contract codes for major forex futures
FOREX_CONTRACTS = {
    "EUR/USD": "099741",
    "GBP/USD": "096742",
    "AUD/USD": "232741",
    "JPY/USD": "097741",
    "CAD/USD": "090741",
    "CHF/USD": "092741",
    "NZD/USD": "112741",
}

def fetch_cot(contract_code: str, contract_name: str) -> dict:
    params = {
        "$filter": f"CFTC_Contract_Market_Code eq '{contract_code}'",
        "$orderby": "Report_Date_as_YYYY_MM_DD desc",
        "$top": 2,
        "$select": (
            "Report_Date_as_YYYY_MM_DD,"
            "NonComm_Positions_Long_All,NonComm_Positions_Short_All,"
            "Comm_Positions_Long_All,Comm_Positions_Short_All,"
            "Change_in_Noncomm_Long_All,Change_in_Noncomm_Short_All,"
            "Change_in_Comm_Long_All,Change_in_Comm_Short_All,"
            "Pct_of_OI_Noncomm_Long_All,Pct_of_OI_Noncomm_Short_All"
        ),
    }
    resp = requests.get(CFTC_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("value", [])
    if len(data) < 1:
        return {}

    latest = data[0]
    prev = data[1] if len(data) > 1 else {}

    spec_long = int(latest.get("NonComm_Positions_Long_All", 0))
    spec_short = int(latest.get("NonComm_Positions_Short_All", 0))
    spec_net = spec_long - spec_short
    spec_net_prev = (
        int(prev.get("NonComm_Positions_Long_All", 0)) -
        int(prev.get("NonComm_Positions_Short_All", 0))
    ) if prev else spec_net

    comm_long = int(latest.get("Comm_Positions_Long_All", 0))
    comm_short = int(latest.get("Comm_Positions_Short_All", 0))
    comm_net = comm_long - comm_short

    spec_pct_long = float(latest.get("Pct_of_OI_Noncomm_Long_All", 0))
    spec_pct_short = float(latest.get("Pct_of_OI_Noncomm_Short_All", 0))

    return {
        "pair": contract_name,
        "report_date": latest.get("Report_Date_as_YYYY_MM_DD"),
        "spec_net": spec_net,
        "spec_net_change": spec_net - spec_net_prev,
        "spec_long": spec_long,
        "spec_short": spec_short,
        "spec_pct_long": spec_pct_long,
        "spec_pct_short": spec_pct_short,
        "comm_net": comm_net,
        "comm_long": comm_long,
        "comm_short": comm_short,
        "bias": "BULLISH" if spec_net > 0 else "BEARISH",
        "contrarian_bias": "SHORT" if spec_net > 0 else "LONG",  # COT contrarian
        "extreme_positioning": abs(spec_pct_long - spec_pct_short) > 20,
    }


def main():
    os.makedirs("data", exist_ok=True)
    results = []
    for name, code in FOREX_CONTRACTS.items():
        print(f"Fetching COT for {name}...")
        try:
            result = fetch_cot(code, name)
            if result:
                results.append(result)
                print(f"  {name}: Spec Net={result['spec_net']:+,} | Contrarian={result['contrarian_bias']}")
        except Exception as e:
            print(f"  ERROR fetching {name}: {e}")

    output = {
        "fetched_at": datetime.utcnow().isoformat(),
        "pairs": results,
    }

    with open("data/cot_latest.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved {len(results)} pairs to data/cot_latest.json")


if __name__ == "__main__":
    main()

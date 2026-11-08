"""JPL Horizons reference positions for the ephemeris cross-check.

Fixtures live in ``tests/fixtures/horizons/<body>.json``: the request
parameters, ``fetched_at``, the parsed rows and the raw Horizons text. They are
fetched once with::

    python -m tests.horizons            # rewrites the fixtures

and the test runs offline against them. ``HORIZONS_LIVE=1`` makes the test
fetch fresh values instead.

Quantity 31 is the observer-centred apparent ecliptic longitude and latitude
of date (IAU76/80 ecliptic, light-time, deflection and aberration applied),
geocentric (``CENTER='500@399'``), at UT instants (``TIME_TYPE='UT'``), from
DE441.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import requests
import swisseph as swe

API = "https://ssd.jpl.nasa.gov/api/horizons.api"
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "horizons"
BODIES: Dict[str, str] = {
    "SUN": "10",
    "MOON": "301",
    "MARS": "499",
    "JUPITER": "599",
    "SATURN": "699",
}
# Six fixed UT instants, 1950 to 2040.
INSTANTS_UTC = [
    (1950, 1, 1, 0.0),
    (1969, 7, 20, 20.0 + 17.0 / 60.0),
    (1987, 3, 15, 6.0),
    (2000, 1, 1, 12.0),
    (2024, 4, 8, 18.0 + 18.0 / 60.0),
    (2040, 6, 15, 0.0),
]
INSTANTS_JD = [swe.julday(y, m, d, h, swe.GREG_CAL) for y, m, d, h in INSTANTS_UTC]


def request_params(command: str) -> Dict[str, str]:
    """Horizons API parameters for one body at :data:`INSTANTS_JD`."""
    return {
        "format": "json",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'500@399'",
        "TLIST": " ".join(f"'{jd:.6f}'" for jd in INSTANTS_JD),
        "TLIST_TYPE": "'JD'",
        "TIME_TYPE": "'UT'",
        "QUANTITIES": "'31'",
        "ANG_FORMAT": "'DEG'",
        "CSV_FORMAT": "'YES'",
        "EXTRA_PREC": "'YES'",
    }


def parse_result(text: str) -> List[Dict]:
    """Rows between ``$$SOE`` and ``$$EOE`` as dicts (lon, lat in degrees)."""
    body = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    rows = []
    for line, jd in zip(
        (ln for ln in body.strip().splitlines() if ln.strip()), INSTANTS_JD
    ):
        fields = [f.strip() for f in line.split(",")]
        rows.append(
            {
                "jd_ut": jd,
                "utc": fields[0],
                "ecl_lon_deg": float(fields[3]),
                "ecl_lat_deg": float(fields[4]),
            }
        )
    if len(rows) != len(INSTANTS_JD):
        raise ValueError(f"expected {len(INSTANTS_JD)} rows, got {len(rows)}")
    return rows


def fetch(body: str, timeout: float = 60.0) -> Dict:
    """Fetch one body from Horizons; returns the fixture document."""
    params = request_params(BODIES[body])
    response = requests.get(API, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"])
    text = payload["result"]
    return {
        "header": {
            "body": body,
            "api": API,
            "params": params,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "signature": payload.get("signature"),
            "quantity": "31: observer apparent ecliptic lon/lat of date (IAU76/80)",
        },
        "rows": parse_result(text),
        "raw_result": text,
    }


def load(body: str) -> Dict:
    """Load the stored fixture for ``body``."""
    return json.loads((FIXTURE_DIR / f"{body.lower()}.json").read_text())


def main() -> None:
    """Refetch and rewrite every fixture."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for body in BODIES:
        doc = fetch(body)
        path = FIXTURE_DIR / f"{body.lower()}.json"
        path.write_text(json.dumps(doc, indent=1) + "\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()

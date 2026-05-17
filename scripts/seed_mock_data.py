"""
Verify all mock data files exist and are valid.
Run: python scripts/seed_mock_data.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path

FILES = {
    "data/mock/tickets.json": "tickets",
    "data/mock/service_metrics.csv": "metrics rows",
    "data/mock/teams_channels.json": "channels",
}

for path, label in FILES.items():
    p = Path(path)
    if not p.exists():
        print(f"MISSING: {path}")
        continue
    if path.endswith(".json"):
        data = json.loads(p.read_text())
        print(f"OK  {path}  ({len(data)} {label})")
    else:
        lines = p.read_text().strip().splitlines()
        print(f"OK  {path}  ({len(lines)-1} {label})")

print("\nMock data ready.")

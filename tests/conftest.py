"""Shared test setup: make `scripts/` importable and provide tiny MSHA-style fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

MINES_HEADER = "MINE_ID|CURRENT_MINE_NAME|CURRENT_CONTROLLER_ID|CURRENT_CONTROLLER_NAME|STATE"
ACCIDENTS_HEADER = 'MINE_ID|DOCUMENT_NO|"SUM(HOURS)"|NARRATIVE'


@pytest.fixture()
def msha_dir(tmp_path: Path) -> Path:
    """Two companies, three mines, accidents with a quoted field and a bad row."""
    d = tmp_path / "msha"
    (d / "Mines").mkdir(parents=True)
    (d / "Accidents").mkdir()
    (d / "Mines" / "Mines.txt").write_bytes(
        "\r\n".join(
            [
                MINES_HEADER,
                "0200001|Alpha Pit|C1|Acme Copper Inc|AZ",
                "0200002|Alpha Mill|C1|Acme Copper Inc|AZ",
                "0300001|Beta Quarry|C2|Other Co|NM",
                "",
            ]
        ).encode("latin-1")
    )
    (d / "Accidents" / "Accidents.txt").write_bytes(
        "\r\n".join(
            [
                ACCIDENTS_HEADER,
                '0200001|D1|10|"Slipped, fell"',
                "0300001|D2|20|other company",
                "0200002|D3|30|caf\xe9 break",
                "0200001|D4|bad row with too|many|fields|here",
                "",
            ]
        ).encode("latin-1")
    )
    return d

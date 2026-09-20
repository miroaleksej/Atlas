"""Integrity of the supplied observational snapshot and row-preserving selection."""
import csv
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/observations/nasa_exoplanet/PSCompPars_2026.09.20_07.33.39.csv'


def test_observational_snapshot_is_unchanged_and_has_unique_planets():
    assert hashlib.sha256(DATA.read_bytes()).hexdigest() == '6129d26e657e1a26256b12fe151886fa28f5530e460578b5d68ab8bda939af9a'
    with DATA.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(line for line in stream if not line.startswith('#')))
    assert len(rows) == 6366
    assert len(rows[0]) == 84
    assert all(row['hostname'].strip() and row['pl_name'].strip() for row in rows)
    assert len({row['pl_name'] for row in rows}) == len(rows)


def test_representative_host_selection_never_fills_from_other_planets():
    pd = pytest.importorskip('pandas')
    from evaluation.exoplanet_nasa2026_blind_experiment import representative_hosts, h64
    names = sorted(['planet-a', 'planet-b'], key=h64)
    frame = pd.DataFrame([
        {'hostname': 'star', 'pl_name': names[0], 'value': float('nan')},
        {'hostname': 'star', 'pl_name': names[1], 'value': 123.0},
    ])
    row = representative_hosts(frame).iloc[0]
    assert row['pl_name'] == names[0]
    assert pd.isna(row['value'])


def test_local_observational_receipt_is_bound_to_source_and_preserves_claim_boundary():
    from source.lawspace.schema import digest_payload
    report = json.loads((ROOT / 'reports/exoplanet/NASA_EXOPLANET_2026_LOCAL_RUN.json').read_text())
    assert report['digest'] == digest_payload({k: v for k, v in report.items() if k != 'digest'})
    assert report['source']['sha256'] == hashlib.sha256(DATA.read_bytes()).hexdigest()
    assert report['residual_multi_axis']['counts'] == {'discovery': 1270, 'validation': 425, 'sealed': 447}
    assert report['claim_boundary']['new_law_claimed'] is False
    assert report['residual_multi_axis']['scientific_law_established'] is False

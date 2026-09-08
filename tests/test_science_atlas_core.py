from pathlib import Path
from source.lawspace.science_atlas_core import ScienceAtlasCoreKernel

ROOT = Path(__file__).resolve().parents[1]


def test_science_atlas_core_owner_is_preserved_but_prior_materialization_is_absent():
    """Clean baseline keeps the regression owner/code, not old computed ledgers."""
    owner = ScienceAtlasCoreKernel(ROOT)
    assert owner is not None
    assert (ROOT / 'source/lawspace/science_atlas_core.py').exists()
    data_dir = ROOT / 'data/science_atlas'
    # A clean sealed baseline may omit an empty directory entirely; if present,
    # it must contain no prior materialized research state.
    assert (not data_dir.exists()) or list(data_dir.iterdir()) == []


def test_atomic_frontier_prior_receipt_is_not_shipped_in_clean_baseline():
    """The owner remains in source; old frontier receipts must not seed a new run."""
    assert (ROOT / 'source/lawspace/atomic_frontier.py').exists()
    assert not (ROOT / 'reports/SEQUENTIAL_PHI_ATOMIC_FRONTIER_CURRENT.json').exists()

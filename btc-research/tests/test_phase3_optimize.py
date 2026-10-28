import pandas as pd
import pytest
from src.phase3_optimize import GRID,grid,training_folds


def test_small_grid_is_predefined():
    configs=grid()
    assert len(configs)==16
    assert len({tuple(sorted(x.items())) for x in configs})==16
    assert set(GRID)=={"atr_stop_multiple","max_hold_minutes",
                       "cooldown_minutes","min_range_to_roundtrip_cost"}


def test_fold_dates_are_chronological_and_do_not_use_holdout():
    start=int(pd.Timestamp("2024-02-03",tz="UTC").timestamp())
    end=int(pd.Timestamp("2026-10-26",tz="UTC").timestamp())
    train_end=int(pd.Timestamp("2025-09-22",tz="UTC").timestamp())
    piece=pd.DataFrame({"time":[start+i*60 for i in range(10)]})
    catalog={"start_utc":pd.to_datetime(start,unit="s",utc=True).isoformat(),
             "end_exclusive_utc":pd.to_datetime(end,unit="s",utc=True).isoformat()}
    with pytest.raises(ValueError,match="Fold has no candles"):
        training_folds(catalog,[piece])
    # Missing folds must fail closed, never silently use validation.
    assert start<train_end<end


def test_too_short_interval_fails_closed():
    start=int(pd.Timestamp("2026-10-20",tz="UTC").timestamp())
    end=int(pd.Timestamp("2026-10-24",tz="UTC").timestamp())
    catalog={"start_utc":pd.to_datetime(start,unit="s",utc=True).isoformat(),
             "end_exclusive_utc":pd.to_datetime(end,unit="s",utc=True).isoformat()}
    with pytest.raises(ValueError):
        training_folds(catalog,[],folds=9)

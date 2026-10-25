import pytest
from src.cloud_backfill import DAY, plan, classify

def test_seven_day_plan():
    assert plan(0,9*DAY)==[(0,7*DAY),(7*DAY,9*DAY)]

def test_skip_fully_covered_by_separate_runs():
    existing=[dict(start=0,end=DAY),dict(start=DAY,end=2*DAY)]
    assert classify([(0,2*DAY),(2*DAY,3*DAY)],existing)==[
        ("skip",0,2*DAY),("fetch",2*DAY,3*DAY)]

def test_partial_overlap_fetches_only_missing_days():
    assert classify([(0,7*DAY)],[dict(start=0,end=2*DAY)])==[("skip",0,2*DAY),("fetch",2*DAY,7*DAY)]

def test_bad_plan():
    with pytest.raises(ValueError): plan(0,0)

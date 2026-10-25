"""Regression tests for safe partial-overlap backfill planning."""
import pytest
from src.cloud_backfill import DAY, classify, plan

def record(lo,hi):
    return {"start":lo*DAY,"end":hi*DAY}

def summarized(items):
    return [(s,a//DAY,b//DAY) for s,a,b in items]

def test_overlap_middle_splits_into_missing_and_skipped():
    windows=plan(0,7*DAY)
    stored=[record(2,4)]
    assert summarized(classify(windows,stored))==[
        ("fetch",0,2),("skip",2,4),("fetch",4,7)]

def test_adjacent_manifests_credit_complete_window():
    assert summarized(classify([(0,7*DAY)],[record(0,2),record(2,7)]))==[
        ("skip",0,2),("skip",2,7)]

def test_gaps_stay_inside_requested_bounds():
    assert summarized(classify([(3*DAY,9*DAY)],[record(0,5),record(7,12)]))==[
        ("skip",3,5),("fetch",5,7),("skip",7,9)]

def test_empty_storage_fetches_each_planned_chunk():
    assert summarized(classify(plan(0,15*DAY),[]))==[
        ("fetch",0,7),("fetch",7,14),("fetch",14,15)]

def test_misaligned_verified_boundary_fails_closed():
    with pytest.raises(ValueError,match="day aligned"):
        classify([(0,3*DAY)],[{"start":DAY//2,"end":DAY}])

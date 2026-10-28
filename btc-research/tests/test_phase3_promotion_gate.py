import copy
import hashlib
import json
import pytest

from src.phase3_optimize import GRID,grid
from src.phase3_promotion_gate import decide


def fixture(tmp_path):
    catalog=tmp_path/"dataset_catalog.json"
    catalog.write_text(json.dumps({"symbol":"BTCUSD","resolution":"1m"}))
    folds=[{"start_utc":f"2025-0{i+1}-01T00:00:00+00:00",
            "end_exclusive_utc":f"2025-0{i+2}-01T00:00:00+00:00"} for i in range(3)]
    candidates=[]
    for idx, params in enumerate(grid(),1):
        results=[{"net_pnl":-10.0,"return_pct":-1.0,"trades":25,
            "profit_factor":.8,"max_drawdown_pct":3.0} for _ in range(3)]
        candidates.append({"id":idx,"parameters":params,"fold_results":results,
            "qualifies":False,"worst_fold_return_pct":-1.0,
            "max_fold_drawdown_pct":3.0,"all_fold_net_pnl":-30.0})
    data={"schema_version":1,"selection_scope":"training_only",
        "validation_evaluated":False,"holdout_evaluated":False,
        "validation":{"status":"reserved"},"holdout":{"status":"locked"},
        "dataset_catalog_sha256":hashlib.sha256(catalog.read_bytes()).hexdigest(),
        "grid":{k:list(v) for k,v in GRID.items()},"min_trades_per_fold":20,
        "folds":folds,"candidates":candidates,"selected_candidate_id":None,
        "decision":"NO_QUALIFYING_CANDIDATE"}
    report=tmp_path/"training_optimization.json"
    report.write_text(json.dumps(data))
    return report,catalog,data


def test_no_candidate_must_stay_locked(tmp_path):
    report,catalog,_=fixture(tmp_path)
    result=decide(report,catalog,"40621068040")
    assert result["decision"]=="REJECTED_NO_QUALIFYING_CANDIDATE"
    assert result["promotion_authorized"] is False
    assert not result["validation_executed"]
    assert not result["holdout_evaluated"]
    assert result["qualified_candidates"]==0


def test_reject_tampered_catalog(tmp_path):
    report,catalog,_=fixture(tmp_path)
    catalog.write_text('{"symbol":"ETHUSD","resolution":"1m"}')
    with pytest.raises(ValueError,match="checksum"):
        decide(report,catalog,"40621068040")


def test_reject_false_promotion_claim(tmp_path):
    report,catalog,data=fixture(tmp_path)
    data["selected_candidate_id"]=1
    report.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="selection mismatch"):
        decide(report,catalog,"40621068040")


def test_reject_unlock_and_inconsistent_fold(tmp_path):
    report,catalog,data=fixture(tmp_path)
    data["validation_evaluated"]=True
    report.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="holdout/validation"):
        decide(report,catalog,"40621068040")
    data["validation_evaluated"]=False
    data["candidates"][0]["fold_results"][0]["return_pct"]=50
    report.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="fold net/return mismatch"):
        decide(report,catalog,"40621068040")


def test_qualifier_does_not_authorize_promotion(tmp_path):
    report,catalog,data=fixture(tmp_path)
    first=data["candidates"][0]
    first["fold_results"]=[{"net_pnl":20.0,"return_pct":2.0,
        "trades":30,"profit_factor":1.5,"max_drawdown_pct":5.0} for _ in range(3)]
    first.update(qualifies=True,worst_fold_return_pct=2.0,
                 max_fold_drawdown_pct=5.0,all_fold_net_pnl=60.0)
    data.update(selected_candidate_id=1,decision="candidate_for_controlled_validation")
    report.write_text(json.dumps(data))
    result=decide(report,catalog,"40621068040")
    assert result["decision"]=="READY_FOR_MANUAL_VALIDATION_REVIEW"
    assert result["promotion_authorized"] is False
    assert result["validation_executed"] is False

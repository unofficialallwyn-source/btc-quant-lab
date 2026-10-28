import hashlib,json
from dataclasses import asdict
from pathlib import Path
import pytest
from src.phase4_decision_gate import decide
from src.phase4_hypotheses import NAMES,Hypothesis,research_specs
from src.risk_engine import RiskPolicy

def fixture(tmp_path):
    catalog=tmp_path/"dataset_catalog.json"
    catalog.write_text(json.dumps({"symbol":"BTCUSD","resolution":"1m"}))
    specs=hashlib.sha256(json.dumps(research_specs(),sort_keys=True).encode()).hexdigest()
    def fold(net=-5.):
        return {"trades":21,"gross_before_slippage":net+2,
            "fees":1.,"slippage":1.,"net_pnl":net,
            "net_return_pct":net/10,"profit_factor":.8,
            "max_drawdown_pct":3.,"win_rate_pct":30.}
    candidate={}
    for name in NAMES:
        rows=[fold() for _ in range(3)]
        candidate[name]={"hypothesis":asdict(Hypothesis(name)),"fold_results":rows,
            "total_trades":63,"total_net_pnl_independent_folds":-15.,
            "worst_fold_return_pct":-.5,"max_fold_drawdown_pct":3.,
            "qualifies_training_gate":False}
    report={"schema_version":1,"phase":"4_step_4","selection_scope":"training_only",
        "validation_evaluated":False,"holdout_evaluated":False,
        "validation":{"status":"reserved"},"holdout":{"status":"locked"},
        "promotion_authorized":False,
        "dataset_catalog_sha256":hashlib.sha256(catalog.read_bytes()).hexdigest(),
        "hypothesis_spec_sha256":specs,
        "risk_policy":asdict(RiskPolicy(entry_mode="transition")),
        "min_trades_per_fold":20,"max_drawdown_pct":25.,
        "folds":[{"start_utc":f"2024-0{i+1}-01T00:00:00+00:00",
                  "end_exclusive_utc":f"2024-0{i+2}-01T00:00:00+00:00"} for i in range(3)],
        "cash_no_trade":{"fold_results":[{"trades":0,"net_pnl":0.,"fees":0.,
          "slippage":0.,"gross_before_slippage":0.,"net_return_pct":0.} for _ in range(3)]},
        "candidates":candidate,"qualifying_hypotheses":[],"decision":"NO_QUALIFYING_CANDIDATE"}
    file=tmp_path/"walkforward_report.json"
    file.write_text(json.dumps(report))
    return file,catalog,report

def test_frozen_rejection(tmp_path):
    f,c,_=fixture(tmp_path)
    d=decide(f,c,"40735017966")
    assert d["decision"]=="REJECTED_NO_QUALIFYING_CANDIDATE"
    assert d["qualified_candidates"]==0
    assert not d["promotion_authorized"]
    assert not d["validation_evaluated"]
    assert not d["holdout_evaluated"]
    assert not d["live_trading_enabled"]

@pytest.mark.parametrize("tamper",[
    lambda r:r.update(validation_evaluated=True),
    lambda r:r["candidates"][NAMES[0]]["fold_results"][0].update(net_pnl=123.),
    lambda r:r["candidates"][NAMES[0]].update(qualifies_training_gate=True),
    lambda r:r.update(decision="TRAINING_CANDIDATES_REQUIRE_MANUAL_REVIEW"),
    lambda r:r.update(hypothesis_spec_sha256="faked"),
    lambda r:r["candidates"].pop(NAMES[-1]),
    lambda r:r["cash_no_trade"]["fold_results"][0].update(net_pnl=10.),
])
def test_tampered_evidence_fails_closed(tmp_path,tamper):
    f,c,r=fixture(tmp_path)
    tamper(r)
    f.write_text(json.dumps(r))
    with pytest.raises(ValueError,match="rejected evidence"):
        decide(f,c,"40735017966")

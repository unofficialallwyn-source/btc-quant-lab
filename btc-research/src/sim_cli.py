"""CLI for deterministic research-only backtest; exports metrics and ledger."""
import argparse
import json
from .sim_engine import Config, run_catalog


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog-dir",required=True)
    p.add_argument("--output",default="data/backtest/baseline")
    p.add_argument("--fee-rate",type=float,default=0.0005)
    p.add_argument("--slippage-rate",type=float,default=0.00025)
    a=p.parse_args()
    c=Config(fee_rate=a.fee_rate,slippage_rate=a.slippage_rate)
    print(json.dumps(run_catalog(a.catalog_dir,a.output,c),indent=2))


if __name__=="__main__":
    main()

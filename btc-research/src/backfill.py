"""CLI historical collector: python -m src.backfill."""
import argparse
from datetime import datetime, timezone
from .delta_client import fetch_candles
from .historical import collect

def utc_epoch(date):
    return int(datetime.strptime(date,'%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())

def main():
    p=argparse.ArgumentParser(description='Read-only Delta India BTC minute backfill')
    p.add_argument('--start',required=True,help='inclusive UTC YYYY-MM-DD')
    p.add_argument('--end',required=True,help='exclusive UTC YYYY-MM-DD')
    p.add_argument('--directory',default='data/raw/BTCUSD/1m')
    p.add_argument('--window-minutes',type=int,default=1800)
    args=p.parse_args()
    start,end=utc_epoch(args.start),utc_epoch(args.end)
    if end <= start or end-start > 7*86400:
        p.error('Run one contiguous window of 1 to 7 UTC days; split larger history into multiple workflow runs')
    if not 1 <= args.window_minutes <= 1800:
        p.error('Delta REST requests must be 1..1800 minutes')
    report=collect(fetch_candles,start,end,args.directory,window_minutes=args.window_minutes)
    print(f'Validated {sum(x["rows"] for x in report)} candles in {len(report)} partitions')

if __name__=='__main__': main()

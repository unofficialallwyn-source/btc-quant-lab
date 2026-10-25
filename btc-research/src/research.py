"""Reproducible research-only BTC Donchian breakout baseline."""
import argparse,json
from pathlib import Path
import pandas as pd
from .ingest import audit,resample

def indicators(b,n=24):
    b=b.copy()
    b['upper']=b.high.shift(1).rolling(n).max()
    b['lower']=b.low.shift(1).rolling(n).min()
    prev=b.close.shift(1)
    tr=pd.concat([b.high-b.low,(b.high-prev).abs(),(b.low-prev).abs()],axis=1).max(axis=1)
    b['atr']=tr.ewm(alpha=1/14,adjust=False).mean()
    b['ema']=b.close.ewm(span=100,adjust=False).mean()
    return b

def backtest(b,start,end,n=24,fee=.0005,slip=.00025):
    b=indicators(b,n).reset_index(drop=True)
    equity=1000.;peak=1000.;dd=0.;position=None;trades=[]
    for i in range(max(120,start),min(end,len(b)-1)):
        bar=b.iloc[i]
        if position:
            s=position['side']; price=None;reason=None
            if (s==1 and bar.low<=position['stop']) or (s==-1 and bar.high>=position['stop']):
                price=min(bar.open,position['stop']) if s==1 else max(bar.open,position['stop']);reason='stop'
            elif (s==1 and bar.high>=position['target']) or (s==-1 and bar.low<=position['target']):
                price=position['target'];reason='target'
            elif i==end-2:
                price=bar.close;reason='end'
            if price is not None:
                price*=1-s*slip
                pnl=s*(price-position['entry'])*position['qty']-fee*(price+position['entry'])*position['qty']
                equity+=pnl
                trades.append({'entry_index':position['i'],'exit_index':i,'side':s,'pnl':pnl,'exit_reason':reason})
                position=None
        peak=max(peak,equity);dd=max(dd,(peak-equity)/peak)
        if position or i>=end-2 or pd.isna(bar.upper) or pd.isna(bar.lower):continue
        s=1 if bar.close>bar.upper and bar.close>bar.ema else -1 if bar.close<bar.lower and bar.close<bar.ema else 0
        if not s:continue
        entry=float(b.iloc[i+1].open)*(1+s*slip)
        dist=float(bar.atr)*1.5
        if dist<=0:continue
        qty=min(equity*.005/dist,equity*2/entry)
        position={'side':s,'entry':entry,'stop':entry-s*dist,'target':entry+s*2*dist,'qty':qty,'i':i+1}
    wins=[x['pnl'] for x in trades if x['pnl']>0]
    losses=[x['pnl'] for x in trades if x['pnl']<0]
    metrics={'starting_equity':1000,'ending_equity':round(equity,2),'return_pct':round((equity/1000-1)*100,2),'trades':len(trades),'win_rate_pct':round(len(wins)/len(trades)*100,2) if trades else None,'profit_factor':round(sum(wins)/-sum(losses),3) if losses else None,'max_drawdown_pct':round(dd*100,2)}
    return metrics,pd.DataFrame(trades)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',default='results');args=ap.parse_args()
    data=pd.read_parquet(args.input)
    quality=audit(data)
    if any(quality[x] for x in ('duplicates','missing_intervals','bad_ohlcv','misaligned')):raise ValueError(f'Invalid candles: {quality}')
    bars=resample(data,5);n=len(bars);splits={'training':(0,int(n*.6)),'validation':(int(n*.6),int(n*.8)),'holdout':(int(n*.8),n)}
    dest=Path(args.output);dest.mkdir(parents=True,exist_ok=True);report={}
    for name,(start,end) in splits.items():
        report[name],ledger=backtest(bars,start,end)
        ledger.to_csv(dest/f'{name}_trades.csv',index=False)
    (dest/'metrics.json').write_text(json.dumps({'audit':quality,'results':report},indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

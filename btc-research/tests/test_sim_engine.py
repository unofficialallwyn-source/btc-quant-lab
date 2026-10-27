import pandas as pd
import pytest
from src.sim_engine import Config, run, breakout_signal


def bars(start=0, closes=(100,100,100,100)):
    return pd.DataFrame({"time":[start+i*60 for i in range(len(closes))],
        "open":list(closes),"high":[x+2 for x in closes],
        "low":[x-2 for x in closes],"close":list(closes),
        "volume":[1.]*len(closes)})


def test_next_open_entry_and_conservative_stop_first():
    frame=bars(closes=(100,100,100))
    # signal at minute 0 enters minute 1; both target and stop touched
    result,trades,curve=run([frame],lambda _: [1,0,0],
        Config(fee_rate=0,slippage_rate=0,stop_pct=.01))
    assert len(trades)==1
    assert trades.iloc[0].entry_time==60
    assert trades.iloc[0].exit_reason=="stop"
    assert trades.iloc[0].net_pnl<0
    assert result["ending_equity"]<1000


def test_fees_and_slippage_reduce_equity():
    frame=bars(closes=(100,100,100))
    cfg=Config(fee_rate=.001,slippage_rate=.001)
    _,trades,_=run([frame],lambda _: [1,0,0],cfg)
    assert trades.iloc[0].fees>0
    assert trades.iloc[0].entry>100
    assert trades.iloc[0].net_pnl < trades.iloc[0].gross_pnl


def test_gap_forces_flat_and_no_signal_carries_forward():
    first=bars(0,(100,100,100))
    second=bars(10*60,(100,100,100))
    result,ledger,curve=run([first,second],lambda f: [1,0,0])
    assert len(ledger)==2
    assert (ledger.groupby("segment_id").size()==1).all()
    assert result["segments"]==2
    assert set(ledger.exit_time).issubset(set(curve.time))


def test_bad_timestamps_and_bad_config_fail_closed():
    bad=bars(0,(100,100,100))
    bad.loc[2,"time"]=240
    with pytest.raises(ValueError,match="timestamps"):
        run([bad],lambda _: [1,0,0])
    with pytest.raises(ValueError,match="1x"):
        run([bars()],lambda _: [0]*4,Config(max_notional_multiple=2))


def test_breakout_uses_past_channel_not_current_bar():
    b=bars(closes=(100,100,100,110,105))
    signals=breakout_signal(b,lookback=3)
    assert signals[3]==1
    assert signals[0]==0

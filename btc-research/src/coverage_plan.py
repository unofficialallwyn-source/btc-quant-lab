"""Plan oldest missing BTC history, preserving already verified Azure ranges."""
from datetime import datetime, timezone
from .cloud_backfill import DAY

def coverage(stored, start, end):
    intervals=sorted((max(start,x["start"]),min(end,x["end"])) for x in stored if x["start"]<end and x["end"]>start)
    merged=[]
    for lo,hi in intervals:
        if merged and lo<=merged[-1][1]:
            merged[-1]=(merged[-1][0],max(hi,merged[-1][1]))
        else:
            merged.append((lo,hi))
    gaps=[]
    pos=start
    for lo,hi in merged:
        if pos<lo: gaps.append((pos,lo))
        pos=max(pos,hi)
    if pos<end: gaps.append((pos,end))
    return merged,gaps

def next_window(stored,start,end,max_days=28):
    if not 1<=max_days<=28: raise ValueError("Invalid max_days")
    _,gaps=coverage(stored,start,end)
    if not gaps: return None
    lo,hi=gaps[0]
    return lo,min(hi,lo+max_days*DAY)

def iso(timestamp):
    return datetime.fromtimestamp(timestamp,timezone.utc).strftime("%Y-%m-%d")

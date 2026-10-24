"""Measure real Lean checks and cache hits; no network or browser required."""
import json, platform, sys, time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import LEVELS, CACHE, parse, verify, rules_ready, source
rules_ready()
rows=[]
for level in LEVELS:
    sample=level['solution']
    program=parse(sample['helpers'],sample['proof'],level)
    CACHE.clear()
    start=time.perf_counter(); first=verify(level,program); elapsed=time.perf_counter()-start
    start=time.perf_counter(); second=verify(level,program); cached=time.perf_counter()-start
    if not first['verified'] or not second['verified']: raise RuntimeError(first)
    rows.append(dict(level=level['id'],lean_ms=round(elapsed*1000,2),cached_ms=round(cached*1000,2),axioms=first['axioms']))
report=dict(measured_at=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),system=platform.system(),architecture=platform.machine(),lean='4.19.0',method='One uncached proof per level after rules precompilation, followed by one cache hit. Local Python API timings; no browser or HTTP latency.',results=rows)
(ROOT/'submission/benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
l=LEVELS[-1];s=l['solution'];(ROOT/'submission/proofs/Level7.lean').write_text(source(l,parse(s['helpers'],s['proof'],l),standalone=True)[0])
print(json.dumps(report,indent=2))

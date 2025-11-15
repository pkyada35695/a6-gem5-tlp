#!/usr/bin/env python3
import sys, re, json, csv, pathlib

def read_kv(path):
    if not path or not path.exists(): return {}
    d={}
    for ln in path.read_text().splitlines():
        if not ln or ln.lstrip().startswith('#'): continue
        sp=ln.split()
        if len(sp)>=2:
            k, v = sp[0], sp[1]
            try: d[k]=float(v)
            except: d[k]=v
    return d

def clock_hz_from_config(cfg):
    if not cfg or not cfg.exists(): return 3e9
    t=cfg.read_text()
    m=re.search(r'clock\s*=\s*(\d+(?:\.\d+)?)\s*([GMk]?Hz)', t)
    if not m: return 3e9
    num,unit=m.groups()
    scale={'Hz':1,'kHz':1e3,'MHz':1e6,'GHz':1e9}.get(unit,1)
    return float(num)*scale

def find_stats_and_cfg(run_dir: pathlib.Path):
    # gem5 may write directly or inside m5out/
    stats = run_dir/'stats.txt'
    cfg   = run_dir/'config.ini'
    if not stats.exists() and (run_dir/'m5out'/'stats.txt').exists():
        stats = run_dir/'m5out'/'stats.txt'
        cfg   = run_dir/'m5out'/'config.ini'
    return stats, cfg

def detect_threads(stats):
    # Count cpuN prefixes; if none, assume 1 (keys like system.cpu.*)
    cpus=set()
    for k in stats.keys():
        m=re.match(r'^system\.cpu(\d+)\.', k)
        if m: cpus.add(int(m.group(1)))
    return (max(cpus)+1) if cpus else 1

def committed_insts(stats):
    total=0.0; found=False
    # 1) per-CPU committedInsts
    for k,v in stats.items():
        if re.match(r'^system\.cpu\d+\.committedInsts$', k):
            total += float(v); found=True
    # 2) thread-level numInsts (commitStats0 or thread_*)
    if not found:
        # sum all commitStats*.numInsts and thread_*.numInsts we find
        for k,v in stats.items():
            if re.match(r'^system\.cpu(\d+)\.commitStats\d+\.numInsts$', k): total += float(v); found=True
            elif re.match(r'^system\.cpu\.commitStats\d+\.numInsts$', k): total += float(v); found=True
            elif re.match(r'^system\.cpu(\d+)?\.thread_\d+\.numInsts$', k): total += float(v); found=True
    # 3) final fallback: system.cpu.committedInsts (single cpu)
    if not found and 'system.cpu.committedInsts' in stats:
        total += float(stats['system.cpu.committedInsts']); found=True
    return total if found else None

def total_cycles(stats, clk_hz, threads):
    # Prefer per-CPU numCycles if present; else derive from simSeconds or simTicks
    had_any=False; cyc_sum=0.0
    for k,v in stats.items():
        if re.match(r'^system\.cpu\d+\.numCycles$', k) or k=='system.cpu.numCycles':
            cyc_sum += float(v); had_any=True
    if had_any: return cyc_sum
    sim_s = stats.get('simSeconds', None)
    if sim_s is None:
        sim_ticks = stats.get('simTicks', None)
        if sim_ticks is not None: sim_s = float(sim_ticks)/float(stats.get('simFreq', 1e12))
    return (sim_s or 0.0)*clk_hz

def extract_one(run_dir: pathlib.Path):
    stats_p, cfg_p = find_stats_and_cfg(run_dir)
    S = read_kv(stats_p)
    if not S: return None
    clk = clock_hz_from_config(cfg_p)

    thr = detect_threads(S)
    ci  = committed_insts(S)
    cyc = total_cycles(S, clk, thr)
    ipc = (ci/cyc) if (ci is not None and cyc and cyc>0) else None
    ss  = S.get('simSeconds', None)
    if ss is None and 'simTicks' in S:
        # fallback: ticks / simFreq (tick/sec)
        ss = float(S['simTicks'])/float(S.get('simFreq', 1e12))

    # Optional: decode op/issue latency if run name is opX_issY_thrZ
    name = run_dir.name
    op=iss=thr_from_name=None
    m=re.match(r'op(\d+)_iss(\d+)_thr(\d+)', name)
    if m: op,iss,thr_from_name = map(int, m.groups())

    return {
        'run': name,
        'threads': thr_from_name if thr_from_name else thr,
        'opLat': op, 'issueLat': iss,
        'simSeconds': ss,
        'totalCommittedInsts': ci,
        'totalCycles': cyc,
        'aggIPC': ipc,
    }

def parse_all(runs_dir: pathlib.Path):
    results={}
    for d in sorted(runs_dir.iterdir()):
        if d.is_dir():
            r=extract_one(d)
            if r: results[d.name]=r
    # Baseline = fastest 1-thread if any; else fastest overall
    base=None
    have_1t = [v for v in results.values() if v.get('threads')==1 and v.get('simSeconds') is not None]
    candidates = have_1t if have_1t else [v for v in results.values() if v.get('simSeconds') is not None]
    for v in candidates:
        if base is None or v['simSeconds']<base: base=v['simSeconds']
    for v in results.values():
        ss=v.get('simSeconds')
        v['speedup_vs_baseline'] = (base/ss) if base and ss else None
    return results

def main():
    root = pathlib.Path('/var/www/html/college/gem5/ilp_part2/runs')
    if len(sys.argv)>1:
        root = pathlib.Path(sys.argv[1])
    if not root.exists():
        print(f"Runs dir not found: {root}"); sys.exit(1)
    out = parse_all(root)
    out_dir = root.parent
    (out_dir/'results.json').write_text(json.dumps(out, indent=2))
    with open(out_dir/'results.csv','w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['run','threads','opLat','issueLat','simSeconds','aggIPC','speedup_vs_baseline','totalCommittedInsts','totalCycles'])
        for k in sorted(out.keys()):
            v=out[k]
            def fmt(x,prec):
                return (f"{x:.{prec}f}" if isinstance(x,(int,float)) and x is not None else "")
            w.writerow([
                v.get('run',""),
                v.get('threads',""),
                v.get('opLat',""),
                v.get('issueLat',""),
                fmt(v.get('simSeconds'),9),
                fmt(v.get('aggIPC'),6),
                fmt(v.get('speedup_vs_baseline'),6),
                int(v['totalCommittedInsts']) if v.get('totalCommittedInsts') is not None else "",
                int(v['totalCycles']) if v.get('totalCycles') is not None else "",
            ])
    print(f"Wrote {out_dir/'results.json'} and {out_dir/'results.csv'}")
if __name__ == "__main__":
    main()

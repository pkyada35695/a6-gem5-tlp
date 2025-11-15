#!/usr/bin/env python3
import sys, re, json, pathlib, csv

def read_stats(path):
    d = {}
    if not path.exists():
        return d
    for ln in path.read_text().splitlines():
        if not ln or ln.lstrip().startswith('#'): 
            continue
        parts = ln.split()
        if len(parts) >= 2:
            k, v = parts[0], parts[1]
            try:
                d[k] = float(v)
            except ValueError:
                d[k] = v
    return d

def clock_hz_from_config(cfg_path):
    if not cfg_path.exists():
        return 3e9
    txt = cfg_path.read_text()
    # Try to find something like "clock = 3GHz"
    m = re.search(r'clock\s*=\s*(\d+(?:\.\d+)?)\s*([GMk]?Hz)', txt)
    if m:
        num, unit = m.groups()
        scale = {'Hz':1, 'kHz':1e3, 'MHz':1e6, 'GHz':1e9}.get(unit, 1)
        return float(num) * scale
    # Fallback
    return 3e9

def extract_run(run_dir):
    run_dir = pathlib.Path(run_dir)
    stats = read_stats(run_dir / "stats.txt")
    if not stats:
        return None

    cfg = run_dir / "config.ini"
    clk = clock_hz_from_config(cfg)

    sim_s = stats.get('simSeconds', None)
    if sim_s is None:
        sim_ticks = stats.get('simTicks', None)
        if sim_ticks is not None:
            sim_s = float(sim_ticks) / clk

    per = []
    i = 0
    total_ci = 0.0
    have_cycles = True
    total_cycles = 0.0
    while True:
        ci = stats.get(f'system.cpu{i}.committedInsts', None)
        cyc = stats.get(f'system.cpu{i}.numCycles', None)
        if ci is None and cyc is None:
            break
        if ci is None:
            ci = 0.0
        total_ci += ci
        per.append({'cpu': i, 'committedInsts': ci, 'numCycles': cyc})
        if cyc is None:
            have_cycles = False
        else:
            total_cycles += cyc
        i += 1

    if i == 0:
        # No per-CPU counters; derive cycles from sim time
        have_cycles = False

    if not have_cycles:
        total_cycles = (sim_s or 0.0) * clk

    agg_ipc = (total_ci / total_cycles) if total_cycles and total_cycles > 0 else None

    return {
        'simSeconds': sim_s,
        'clockHz': clk,
        'totalCommittedInsts': total_ci,
        'totalCycles': total_cycles,
        'aggIPC': agg_ipc,
        'perCPU': per
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: parse_stats.py <runs_dir>")
        sys.exit(1)

    runs_dir = pathlib.Path(sys.argv[1])
    if not runs_dir.exists():
        print(f"Runs dir not found: {runs_dir}")
        sys.exit(2)

    results = {}
    for d in sorted(runs_dir.iterdir()):
        if not d.is_dir():
            continue
        m = re.match(r'op(\d+)_iss(\d+)_thr(\d+)', d.name)
        if not m:
            continue
        op, iss, thr = map(int, m.groups())
        r = extract_run(d)
        if not r:
            continue
        r.update({'opLat': op, 'issueLat': iss, 'threads': thr})
        results[d.name] = r

    # Baseline = fastest 1-thread run (smallest simSeconds)
    baseline = None
    for k, v in results.items():
        if v['threads'] == 1 and v['simSeconds'] is not None:
            if baseline is None or v['simSeconds'] < baseline:
                baseline = v['simSeconds']

    for v in results.values():
        ss = v.get('simSeconds', None)
        v['speedup_vs_best_1thread'] = (baseline / ss) if baseline and ss else None

    # Write JSON
    out_dir = runs_dir.parent
    (out_dir / 'results.json').write_text(json.dumps(results, indent=2))

    # Write CSV (safe via csv.writer)
    csv_path = out_dir / 'results.csv'
    headers = [
        'run','opLat','issueLat','threads',
        'simSeconds','aggIPC','speedup_vs_best_1thread',
        'totalCommittedInsts','totalCycles'
    ]
    with open(csv_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(headers)
        for k in sorted(results.keys()):
            v = results[k]
            w.writerow([
                k,
                v['opLat'],
                v['issueLat'],
                v['threads'],
                f"{v['simSeconds']:.9f}" if v['simSeconds'] is not None else "",
                f"{v['aggIPC']:.6f}" if v['aggIPC'] is not None else "",
                f"{v['speedup_vs_best_1thread']:.6f}" if v['speedup_vs_best_1thread'] is not None else "",
                int(v['totalCommittedInsts']) if v['totalCommittedInsts'] is not None else "",
                int(v['totalCycles']) if v['totalCycles'] is not None else ""
            ])

    print(f"Wrote {out_dir/'results.json'} and {csv_path}")

if __name__ == "__main__":
    main()

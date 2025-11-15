# a6-gem5-tlp
Assignment 6 — Exploring Thread-Level Parallelism (TLP) in shared-memory multiprocessors using gem5 (MinorCPU).  
Workload: pthreads DAXPY. Sweep Float/Simd FU latencies where `opLat + issueLat = 7` and threads in `{1,2,4,8}`.

## Quick Start
```bash
# from repo root
cd tlp_part2

# (1) build benchmark
gcc -O3 -pthread -static bench/daxpy_mt.c -o bench/daxpy_mt || gcc -O3 -pthread bench/daxpy_mt.c -o bench/daxpy_mt

# (2) run experiments (creates runs/op*_iss*_thr*/…)
./run_experiments.sh

# (3) parse results → results.csv / results.json
./parse_stats.py ./runs

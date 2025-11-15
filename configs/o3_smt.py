# One DerivO3CPU core with 1 thread, SE mode, gem5 v23-friendly (for testing).
from m5.objects import *
import m5, argparse

p = argparse.ArgumentParser()
p.add_argument("--cmd", required=True)
p.add_argument("--width", type=int, default=4)
args = p.parse_args()

sys = System()
sys.clk_domain = SrcClockDomain(clock="2GHz", voltage_domain=VoltageDomain())
sys.mem_mode = "timing"
sys.mem_ranges = [AddrRange("512MB")]

# Simple bus + memory
sys.membus = SystemXBar()
sys.system_port = sys.membus.cpu_side_ports
sys.mem_ctrl = MemCtrl(dram=DDR3_1600_8x8())
sys.mem_ctrl.port = sys.membus.mem_side_ports

# CPU: 1 core, 1 thread
cpu = DerivO3CPU()
cpu.numThreads = 1

# superscalar widths
for attr in ["fetchWidth","decodeWidth","renameWidth",
             "issueWidth","dispatchWidth","commitWidth"]:
    setattr(cpu, attr, args.width)

cpu.branchPred = TournamentBP()
sys.cpu = cpu

# connect directly (no private caches to avoid version-specific config)
cpu.icache_port = sys.membus.cpu_side_ports
cpu.dcache_port = sys.membus.cpu_side_ports

# Create single process
proc = Process()
proc.cmd = [args.cmd]
proc.pid = 100
proc.uid = 100

# Assign workload
sys.workload = [proc]
cpu.workload = [proc]

root = Root(full_system=False, system=sys)
m5.instantiate()

# Create thread context
cpu.createThreadContext(0)

m5.simulate()
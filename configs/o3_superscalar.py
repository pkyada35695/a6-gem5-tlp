from m5.objects import *
import m5, argparse

parser = argparse.ArgumentParser()
parser.add_argument('--cmd', required=True)
parser.add_argument('--width', type=int, default=4)  # superscalar width
args = parser.parse_args()

sys = System()
sys.clk_domain = SrcClockDomain(clock="2GHz", voltage_domain=VoltageDomain())
sys.mem_mode = 'timing'
sys.mem_ranges = [AddrRange('512MB')]
sys.membus = SystemXBar()
sys.system_port = sys.membus.cpu_side_ports

cpu = DerivO3CPU()
# Set widths (fetch/dispatch/issue/commit)
cpu.fetchWidth = args.width
cpu.decodeWidth = args.width
cpu.renameWidth = args.width
cpu.issueWidth = args.width
cpu.dispatchWidth = args.width
cpu.commitWidth = args.width

# Reasonable ROB/IQ sizes
cpu.numROBEntries = 192
cpu.numIQEntries  = 64
cpu.LQEntries     = 32
cpu.SQEntries     = 32

# Simple dynamic predictor (Tournament works well)
cpu.branchPred = TournamentBP()

# L1 + private L2 for less memory stalls (keep tiny)
cpu.icache = Cache(size='32kB', assoc=2)
cpu.dcache = Cache(size='32kB', assoc=2)
cpu.l2cache = Cache(size='256kB', assoc=8)
cpu.icache.connectCPU(cpu.icache_port)
cpu.dcache.connectCPU(cpu.dcache_port)
cpu.icache.connectBus(sys.membus)
cpu.dcache.connectBus(sys.membus)
cpu.l2cache.cpu_side = sys.membus.mem_side_ports
cpu.l2cache.mem_side = sys.membus.cpu_side_ports  # simple path

sys.cpu = cpu
sys.mem_ctrl = MemCtrl(dram=DDR3_1600_8x8())
sys.mem_ctrl.port = sys.membus.mem_side_ports

proc = Process()
proc.cmd = [args.cmd]
sys.cpu.workload = proc
sys.cpu.createThreads()

root = Root(full_system=False, system=sys)
m5.instantiate()
m5.simulate()

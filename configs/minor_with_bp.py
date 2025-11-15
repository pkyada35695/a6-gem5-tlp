from m5.objects import *
import m5, argparse

parser = argparse.ArgumentParser()
parser.add_argument('--cmd', required=True)
parser.add_argument('--bp', choices=['static','local'], default='static')
args = parser.parse_args()

system = System()
system.clk_domain = SrcClockDomain(clock="2GHz", voltage_domain=VoltageDomain())
system.mem_mode = 'timing'
system.mem_ranges = [AddrRange('512MB')]
system.membus = SystemXBar()
system.system_port = system.membus.cpu_side_ports

cpu = MinorCPU()

if args.bp == 'static':
    cpu.branchPred = StaticBP()       # always predict not-taken (simple)
else:
    cpu.branchPred = LocalBP()        # simple dynamic local predictor

cpu.icache = Cache(size='32kB', assoc=2)
cpu.dcache = Cache(size='32kB', assoc=2)
cpu.icache.connectCPU(cpu.icache_port)
cpu.dcache.connectCPU(cpu.dcache_port)
cpu.icache.connectBus(system.membus)
cpu.dcache.connectBus(system.membus)

system.cpu = cpu
system.mem_ctrl = MemCtrl(dram=DDR3_1600_8x8())
system.mem_ctrl.port = system.membus.mem_side_ports

process = Process()
process.cmd = [args.cmd]
system.cpu.workload = process
system.cpu.createThreads()

root = Root(full_system=False, system=system)
m5.instantiate()
m5.simulate()

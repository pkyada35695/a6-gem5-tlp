from m5.objects import *
import m5
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--cmd', required=True)
args = parser.parse_args()

system = System()
system.clk_domain = SrcClockDomain(clock="2GHz", voltage_domain=VoltageDomain())
system.mem_mode = 'timing'
system.mem_ranges = [AddrRange('512MB')]

# Simple memory system
system.membus = SystemXBar()
system.system_port = system.membus.cpu_side_ports

# In-order CPU (Minor) -> 4 conceptual pipeline stages
system.cpu = MinorCPU()

# L1 caches (tiny, just to be realistic)
system.cpu.icache = Cache(size='32kB', assoc=2)
system.cpu.dcache = Cache(size='32kB', assoc=2)
system.cpu.icache.connectCPU(system.cpu.icache_port)
system.cpu.dcache.connectCPU(system.cpu.dcache_port)
system.cpu.icache.connectBus(system.membus)
system.cpu.dcache.connectBus(system.membus)

# Simple memory controller + DRAM
system.mem_ctrl = MemCtrl(dram=DDR3_1600_8x8())
system.mem_ctrl.port = system.membus.mem_side_ports

# Workload (SE mode)
process = Process()
process.cmd = [args.cmd]
system.cpu.workload = process
system.cpu.createThreads()

root = Root(full_system=False, system=system)
m5.instantiate()
exit_event = m5.simulate()
print(exit_event.getCause())

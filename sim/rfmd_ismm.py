from migen.flow.network import *
from migen.flow.transactions import *
from migen.actorlib.sim import *
from migen.sim.generic import Simulator, TopLevel

from library.rf_drivers import *

class DataGen(SimActor):
	def __init__(self):
		self.ismm = Source([("addr", 7), ("data", 16)])
		def data_gen():
			yield Token("ismm", {"addr": 0b1010010, "data": 0})
			for i in range(16):
				yield Token("ismm", {"addr": 0b1010101, "data": 1 << i})
		SimActor.__init__(self, data_gen())

class RFMDISMM:
	def __init__(self):
		self.enx = Signal()
		self.sclk = Signal()
		self.sdata = Signal()
		self.sdatao = Signal()

def main():
	g = DataFlowGraph()
	g.add_connection(DataGen(), RFMDISMMDriver(RFMDISMM()))
	c = CompositeActor(g)
	
	def end_simulation(s):
		s.interrupt = s.cycle_counter > 5 and not s.rd(c.busy)
	f = c.get_fragment() + Fragment(sim=[end_simulation])
	sim = Simulator(f, TopLevel(vcd_name="rfmd_ismm.vcd"))
	sim.run()

main()

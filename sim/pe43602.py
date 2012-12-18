from migen.flow.network import *
from migen.flow.transactions import *
from migen.actorlib.sim import *
from migen.sim.generic import Simulator, TopLevel
from migen.sim.icarus import Runner

from library.rf_drivers import *

class DataGen(SimActor):
	def __init__(self):
		def data_gen():
			yield Token("attn", {"attn": 0b11010010})
			for i in range(7):
				yield Token("attn", {"attn": 1 << i})
		SimActor.__init__(self, data_gen(),
			("attn", Source, [("attn", 8)]))

def main():
	g = DataFlowGraph()
	g.add_connection(DataGen(), PE43602Driver())
	c = CompositeActor(g)
	
	def end_simulation(s):
		s.interrupt = s.cycle_counter > 5 and not s.rd(c.busy)
	f = c.get_fragment() + Fragment(sim=[end_simulation])
	sim = Simulator(f, Runner(), TopLevel(vcd_name="pe43602.vcd"))
	sim.run()

main()

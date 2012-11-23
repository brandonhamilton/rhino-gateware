from migen.flow.network import *
from migen.actorlib.sim import *
from migen.bus import wishbone
from migen.bus.transactions import *
from migen.pytholite.transel import *
from migen.pytholite.compiler import make_pytholite
from migen.sim.generic import Simulator
from migen.sim.icarus import Runner
from migen.fhdl import verilog

# TX table entry format:
#   0: <pad.1> <ctrl.3> <waveform.4>
#   1: <attn.8>
#   2: <pad.1> <mod_addr0.7>
#   3: <mod_data0H.8>
#   4: <mod_data0L.8>
#   5: <pad.1> <mod_addr1.7>
#   6: <mod_data1H.8>
#   7: <mod_data1L.8>
#   8: <pad.1> <mod_addr2.7>
#   9: <mod_data2H.8>
#  10: <mod_data2L.8>
#  11: <pad.1> <mod_addr3.7>
#  12: <mod_data3H.8>
#  13: <mod_data3L.8>
#  14: <pad.8>
#  15: <pad.8>

def tx_programmer():
	a = Register(8)
	ctl = Register(8)
	d1 = Register(8)
	d2 = Register(8)
	d3 = Register(8)
	
	while True:
		# receive address
		t = Token("address")
		yield t
		a.store = t.value["a"] << 4
	
		r = TRead(a)
		yield r
		ctl.store = r.data
		
		# send programming information
		if bitslice(ctl, 6):
			yield Token("wave", {"wave": bitslice(ctl, 0, 4)})
		if bitslice(ctl, 5):
			r = TRead(a + 1)
			yield r
			d1.store = r.data
			yield Token("attn", {"attn": d1})
		if bitslice(ctl, 4):
			for i in [2, 5, 8]:
				r = TRead(a + i)
				yield r
				d1.store = r.data
				r = TRead(a + i + 1)
				yield r
				d2.store = r.data
				r = TRead(a + i + 2)
				yield r
				d3.store = r.data
				yield Token("mod", {
					"addr": bitslice(d1, 0, 7),
					"data": (d2 << 8) | d3})

class AdrGen(SimActor):
	def __init__(self):
		def adr_gen():
			yield Token("address", {"a": 0})
		super().__init__(adr_gen(),
			("address", Source, [("a", BV(4))]))
	
class Dumper(SimActor):
	def __init__(self, layout):
		def dumper_gen():
			while True:
				t = Token("result")
				yield t
				print(t.value)
		super().__init__(dumper_gen(),
			("result", Sink, layout))

def main():
	table = Memory(8, 256, init=[
		0x73,
		0x42
	])
	
	rp = make_pytholite(tx_programmer,
		dataflow=[
			("address", Sink, [("a", BV(4))]),
			("wave", Source, [("wave", BV(4))]),
			("attn", Source, [("attn", BV(8))]),
			("mod", Source, [("addr", BV(7)), ("data", BV(16))])
		],
		buses={"table": table})
	
	n_adrgen = ActorNode(AdrGen())
	n_rp = ActorNode(rp)
	n_dump_wave = ActorNode(Dumper([("a", BV(4))]))
	n_dump_attn = ActorNode(Dumper([("attn", BV(8))]))
	n_dump_mod = ActorNode(Dumper([("addr", BV(7)), ("data", BV(16))]))
	
	g = DataFlowGraph()
	g.add_connection(n_adrgen, n_rp)
	g.add_connection(n_rp, n_dump_wave, "wave")
	g.add_connection(n_rp, n_dump_attn, "attn")
	g.add_connection(n_rp, n_dump_mod, "mod")
	c = CompositeActor(g)
	
	sim = Simulator(c.get_fragment(), Runner())
	sim.run(100)

main()

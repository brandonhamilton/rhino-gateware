from migen.fhdl.structure import *
from migen.flow.network import *
from migen.actorlib.sim import Token # TODO: move this
from migen.actorlib.spi import *
from migen.bus.transactions import *
from migen.pytholite.transel import *
from migen.pytholite.compiler import make_pytholite

from library.uid import UID_RF_PROGRAMMER
from library.rf_drivers import *

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

def _programmer():
	a = Register(16) # FIXME
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

class RFProgrammerCore:
	def __init__(self, table_size):
		n_tx_entries_bits = bits_for(table_size//16-1)
		
		# table
		self.table = Memory(8, table_size)
		
		# dataflow components
		self._trigger = SingleGenerator([("a", n_tx_entries_bits)], MODE_SINGLE_SHOT)
		self._programmer = make_pytholite(_programmer,
			dataflow=[
				("address", Sink, [("a", n_tx_entries_bits)]),
				("wave", Source, [("wave", 4)]),
				("attn", Source, [("attn", 8)]),
				("mod", Source, [("addr", 7), ("data", 16)])
			],
			buses={
				"table": self.table
			})
		self.attenuator_driver = PE43602Driver()
		self.modulator_driver = RFMD2081Driver()
		
		# dataflow network
		# TODO: connect to waveform generator
		# TODO: remove ActorNode from Migen
		trigger = ActorNode(self._trigger)
		programmer = ActorNode(self._programmer)
		attenuator_driver = ActorNode(self.attenuator_driver)
		modulator_driver = ActorNode(self.modulator_driver)
		g = DataFlowGraph()
		g.add_connection(trigger, programmer)
		g.add_connection(programmer, attenuator_driver, "attn")
		g.add_connection(programmer, modulator_driver, "mod")
		self._network = CompositeActor(g)
		self._busy = RegisterField("busy", access_bus=READ_ONLY, access_dev=WRITE_ONLY)
	
	def get_registers(self):
		return self._trigger.get_registers() + \
		  [self._busy] + \
		  self.attenuator_driver.get_registers() + self.modulator_driver.get_registers()
	
	def get_memories(self):
		return [self.table]
	
	def get_fragment(self):
		bf = Fragment([self._busy.field.w.eq(self._network.busy)])
		return bf + self._network.get_fragment()

class RFProgrammer:
	def __init__(self, baseapp, table_size=1024):
		self.core = RFProgrammerCore(table_size)
		self.attenuator_pins = baseapp.constraints.request("pe43602")
		self.modulator_pins = baseapp.constraints.request("rfmd2081")
		
		baseapp.csrs.request("rfp", UID_RF_PROGRAMMER, *self.core.get_registers(),
			memories=self.core.get_memories())
	
	def get_fragment(self):
		comb = [
			self.attenuator_pins.d.eq(self.core.attenuator_driver.d),
			self.attenuator_pins.clk.eq(self.core.attenuator_driver.clk),
			self.attenuator_pins.le.eq(self.core.attenuator_driver.le),
			
			self.modulator_pins.enx.eq(self.core.modulator_driver.enx),
			self.modulator_pins.sclk.eq(self.core.modulator_driver.sclk),
			self.modulator_pins.sdata.eq(self.core.modulator_driver.sdata),
			self.core.modulator_driver.sdatao.eq(self.modulator_pins.sdatao)
		]
		return Fragment(comb) + self.core.get_fragment()

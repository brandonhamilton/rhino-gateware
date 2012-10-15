from math import sin, pi

import matplotlib.pyplot as plt

from migen.bus.transactions import *
from migen.bus import csr
from migen.bank import csrgen
from migen.actorlib.sim import *
from migen.flow.network import *
from migen.sim.generic import Simulator
from migen.sim.icarus import Runner

from library.waveform_generator import WaveformGenerator

# The WaveformGenerator component gives an abstract list of registers.
# This derived class implements it on a CSR bus.
class CSRWG(WaveformGenerator):
	def __init__(self, address, depth, width=16, spc=1):
		super().__init__(depth, width, spc)
		self.bank = csrgen.Bank(self.get_registers(), address)
	
	def get_fragment(self):
		return super().get_fragment() + self.bank.get_fragment()

width = 16
depth = 512
values = [int((2**(width-1) - 1)*(sin(2*pi*x/depth) + 1)) for x in range(depth)]

received_values = []

csr_mode = 0
csr_busy = 1
csr_size_h = 2
csr_size_l = 3
csr_mult_h = 4
csr_mult_l = 5
csr_data_in_h0 = 6
csr_data_in_l0 = 7
csr_data_in_h1 = 8
csr_data_in_l1 = 9
csr_shift_data = 10

def programmer():
	# Go to "load waveform" mode
	yield TWrite(csr_mode, 1)
	# Load the waveform
	for v0, v1 in zip(values[0::2], values[1::2]):
		yield TWrite(csr_data_in_h0, (v0 & 0xff00) >> 8)
		yield TWrite(csr_data_in_l0, v0 & 0x00ff)
		yield TWrite(csr_data_in_h1, (v1 & 0xff00) >> 8)
		yield TWrite(csr_data_in_l1, v1 & 0x00ff)
		yield TWrite(csr_shift_data, 1)
	
	# Go to playback mode, default multiplier is 1
	yield TWrite(csr_mode, 2)
	# Wait for the collection of 2 periods
	while len(received_values) < 2*depth:
		yield None
	
	# Set new multiplier
	yield TWrite(csr_mult_l, 2)
	# Collect values
	while len(received_values) < 3*depth:
		yield None
	
	# Set new multiplier
	yield TWrite(csr_mult_l, 12)
	# Collect values
	while len(received_values) < 4*depth:
		yield None

def receiver():
	while True:
		t = Token("sample")
		yield t
		received_values.append(t.value["value0"])
		received_values.append(t.value["value1"])

def main():
	# Create a simple dataflow system
	wg = ActorNode(CSRWG(0, depth, width, 2))
	sink = ActorNode(SimActor(receiver(), ("sample", Sink, [("value0", BV(width)), ("value1", BV(width))])))
	g = DataFlowGraph()
	g.add_connection(wg, sink)
	comp = CompositeActor(g)
	
	# CSR programmer and interconnect
	csr_prog = csr.Initiator(programmer())
	csr_intercon = csr.Interconnect(csr_prog.bus, [wg.actor.bank.interface])

	# Run the simulation until the CSR programmer finishes
	def end_simulation(s):
		s.interrupt = csr_prog.done
	frag = comp.get_fragment() + csr_prog.get_fragment() + csr_intercon.get_fragment() \
		+ Fragment(sim=[end_simulation])
	sim = Simulator(frag, Runner())
	sim.run()
	
	# Check correctness of the first received values
	assert(received_values[:depth] == values)
	
	# Plot waveform
	plt.plot(received_values)
	plt.show()

main()

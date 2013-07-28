from migen.fhdl.std import *
from migen.genlib.cdc import MultiReg
from migen.bank.description import *

class GPIOIn(Module, AutoCSR):
	def __init__(self, signal):
		self._r_in = CSRStatus(flen(signal))
		self.specials += MultiReg(signal, self._r_in.status)

class GPIOOut(Module, AutoCSR):
	def __init__(self, signal):
		self._r_out = CSRStorage(flen(signal), reset=3)
		self.comb += signal.eq(self._r_out.storage)

class Blinker(Module):
	def __init__(self, signal, divbits=26):
		counter = Signal(divbits)
		self.comb += signal.eq(counter[divbits-1])
		self.sync += counter.eq(counter + 1)

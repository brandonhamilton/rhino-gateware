from migen.fhdl.structure import *
from migen.fhdl.module import Module
from migen.bank.description import AutoCSR

from library.waveform_memory import WaveformMemoryOut, WaveformMemoryIn
from library.ti_io import DAC, DAC2X, ADC

class WaveformGenerator(Module, AutoCSR):
	def __init__(self, crg, pads, double_dac):
		width = 2*len(pads.dat_p)
		spc = 2 if double_dac else 1
		dac_class = DAC2X if double_dac else DAC
		self.submodules.wm = WaveformMemoryOut(1024, width, spc)
		self.submodules.dac = dac_class(pads, crg.dacio_strb)
	
		if double_dac:
			self.comb += [
				self.dac.i0.eq(self.wm.value_i0),
				self.dac.q0.eq(self.wm.value_q0),
				self.dac.i1.eq(self.wm.value_i1),
				self.dac.q1.eq(self.wm.value_q1)
			]
		else:
			self.comb += [
				self.dac.i.eq(self.wm.value_i0),
				self.dac.q.eq(self.wm.value_q0)
			]

class WaveformCollector(Module, AutoCSR):
	def __init__(self, pads_or_adc):
		if isinstance(pads_or_adc, Module):
			self.adc = pads_or_adc
			self.autocsr_exclude = {"adc"}
		else:
			self.submodules.adc = ADC(pads_or_adc)
		width = len(self.adc.a)
		self.submodules.wm = WaveformMemoryIn(1024, 2*width)

		self.comb += self.wm.value.eq(Cat(self.adc.a, self.adc.b))

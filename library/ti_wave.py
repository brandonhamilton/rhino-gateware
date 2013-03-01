from migen.fhdl.structure import *
from migen.fhdl.specials import Memory
from migen.bank.description import *
from migen.genlib.cdc import MultiReg

from library.uid import UID_WAVEFORM_GENERATOR, UID_WAVEFORM_COLLECTOR
from library.ti_io import DAC, DAC2X, ADC

class WaveformMemory:
	def __init__(self, depth, width, spc):
		self.depth = depth
		self.width = width
		self.spc = spc

		self._mem = Memory(self.width, self.depth)
		
		# registers are in the system clock domain
		self._r_play_en = RegisterField("playback_en")
		self._r_size = RegisterField("size", bits_for(self.depth), reset=self.depth)
		self._r_mult = RegisterField("mult", bits_for(self.depth), reset=1)

		# register data transferred to signal clock domain
		self._play_en = Signal()
		self._size = Signal(bits_for(self.depth))
		self._mult = Signal(bits_for(self.depth))
		
		# data interface, in signal clock domain
		for i in range(self.spc):
			name = "value" + str(i)
			setattr(self, name, Signal(self.width, name=name))

	def get_registers(self):
		return [self._r_play_en, self._r_size, self._r_mult]

	def get_memories(self):
		return [self._mem]
		
	def get_fragment(self):
		# transfer register data to signal clock domain
		specials = {
			MultiReg(self._r_play_en.field.r, "sys", self._play_en, "signal"),
			MultiReg(self._r_size.field.r, "sys", self._size, "signal"),
			MultiReg(self._r_mult.field.r, "sys", self._mult, "signal"),
		}

		# memory
		mem_ports = [self._mem.get_port(clock_domain="signal") 
			for i in range(self.spc)]
		specials.add(self._mem)
		
		# logic
		sync = []
		for n, port in enumerate(mem_ports):
			v_mem_a = Signal(bits_for(self.depth-1)+1, variable=True)
			sync += [
				v_mem_a.eq(port.adr),
				If(~self._play_en,
					v_mem_a.eq(n*self._mult)
				).Else(
					v_mem_a.eq(v_mem_a + self.spc*self._mult)
				),
				If(v_mem_a >= self._size,
					v_mem_a.eq(v_mem_a - self._size)
				),
				port.adr.eq(v_mem_a),

				getattr(self, "value" + str(n)).eq(port.dat_r)
			]
		
		return Fragment(sync={"signal": sync}, specials=specials)

class WaveformGenerator:
	def __init__(self, baseapp):
		dac_pins = baseapp.mplat.request("ti_dac")
		width = 2*len(dac_pins.dat_p)
		
		self._double_dac = baseapp.double_dac
		spc = 2 if self._double_dac else 1
		dac_class = DAC2X if self._double_dac else DAC
		
		self._wg_i = WaveformMemory(1024, width, spc)
		self._wg_q = WaveformMemory(1024, width, spc)
		self._dac = dac_class(dac_pins, baseapp.crg.dacio_strb)

		registers = regprefix("i_", self._wg_i.get_registers()) \
			+ regprefix("q_", self._wg_q.get_registers()) \
			+ self._dac.get_registers()
		memories = memprefix("i_", self._wg_i.get_memories()) \
			+ memprefix("q_", self._wg_q.get_memories())
		baseapp.csrs.request("wg", UID_WAVEFORM_GENERATOR, *registers, memories=memories)
	
	def get_fragment(self):
		if self._double_dac:
			comb = [
				self._dac.i0.eq(self._wg_i.value0),
				self._dac.q0.eq(self._wg_q.value0),
				self._dac.i1.eq(self._wg_i.value1),
				self._dac.q1.eq(self._wg_q.value1)
			]
		else:
			comb = [
				self._dac.i.eq(self._wg_i.value0),
				self._dac.q.eq(self._wg_q.value0)
			]
		return self._wg_i.get_fragment() + self._wg_q.get_fragment() \
			+ self._dac.get_fragment() + Fragment(comb)

class WaveformCollector:
	def __init__(self, baseapp):
		#adc_pins = baseapp.mplat.request("ti_adc")
		#adc = ADC(adc_pins)
		#baseapp.csrs.request("wc", UID_WAVEFORM_COLLECTOR, *wc.get_registers())
		pass # TODO

	def get_fragment(self):
		return Fragment()

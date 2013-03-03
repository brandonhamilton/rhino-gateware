from migen.fhdl.structure import *
from migen.fhdl.specials import Memory
from migen.fhdl.autofragment import FModule
from migen.bank.description import *
from migen.genlib.cdc import MultiReg, PulseSynchronizer

from library.uid import UID_WAVEFORM_GENERATOR, UID_WAVEFORM_COLLECTOR
from library.ti_io import DAC, DAC2X, ADC

class WaveformMemoryOut(FModule):
	def __init__(self, depth, width, spc):
		self.depth = depth
		self.width = width
		self.spc = spc

		self._mem = Memory(self.width, self.depth)
		
		# registers are in the system clock domain
		self._r_play_en = RegisterField("playback_en")
		self._r_size = RegisterField("size", bits_for(self.depth), reset=self.depth)
		self._r_mult = RegisterField("mult", bits_for(self.depth), reset=1)
		
		# data interface, in signal clock domain
		for i in range(self.spc):
			name = "value" + str(i)
			setattr(self, name, Signal(self.width, name=name))

	def get_registers(self):
		return [self._r_play_en, self._r_size, self._r_mult]

	def get_memories(self):
		return [self._mem]
		
	def build_fragment(self):
		# register data transferred to signal clock domain
		play_en = Signal()
		size = Signal(bits_for(self.depth))
		mult = Signal(bits_for(self.depth))
		self.specials += {
			MultiReg(self._r_play_en.field.r, "sys", play_en, "signal"),
			MultiReg(self._r_size.field.r, "sys", size, "signal"),
			MultiReg(self._r_mult.field.r, "sys", mult, "signal"),
		}
		#
		mem_ports = [self._mem.get_port(clock_domain="signal") 
			for i in range(self.spc)]
		for n, port in enumerate(mem_ports):
			v_mem_a = Signal(bits_for(self.depth-1)+1, variable=True)
			self.sync.signal += [
				v_mem_a.eq(port.adr),
				If(~play_en,
					v_mem_a.eq(n*mult)
				).Else(
					v_mem_a.eq(v_mem_a + self.spc*mult)
				),
				If(v_mem_a >= size,
					v_mem_a.eq(v_mem_a - size)
				),
				port.adr.eq(v_mem_a),
				getattr(self, "value" + str(n)).eq(port.dat_r)
			]

class WaveformGenerator(FModule):
	def __init__(self, baseapp):
		dac_pins = baseapp.mplat.request("ti_dac")
		width = 2*len(dac_pins.dat_p)
		
		self._double_dac = baseapp.double_dac
		spc = 2 if self._double_dac else 1
		dac_class = DAC2X if self._double_dac else DAC
		
		self._wm_i = WaveformMemoryOut(1024, width, spc)
		self._wm_q = WaveformMemoryOut(1024, width, spc)
		self._dac = dac_class(dac_pins, baseapp.crg.dacio_strb)

		registers = regprefix("i_", self._wm_i.get_registers()) \
			+ regprefix("q_", self._wm_q.get_registers()) \
			+ self._dac.get_registers()
		memories = memprefix("i_", self._wm_i.get_memories()) \
			+ memprefix("q_", self._wm_q.get_memories())
		baseapp.csrs.request("wg", UID_WAVEFORM_GENERATOR, *registers, memories=memories)
	
	def build_fragment(self):
		if self._double_dac:
			self.comb += [
				self._dac.i0.eq(self._wm_i.value0),
				self._dac.q0.eq(self._wm_q.value0),
				self._dac.i1.eq(self._wm_i.value1),
				self._dac.q1.eq(self._wm_q.value1)
			]
		else:
			self.comb += [
				self._dac.i.eq(self._wm_i.value0),
				self._dac.q.eq(self._wm_q.value0)
			]

class WaveformMemoryIn(FModule):
	def __init__(self, depth, width):
		self.depth = depth
		self.width = width

		self._mem = Memory(self.width, self.depth)
		
		# registers are in the system clock domain
		self._r_start = RegisterRaw("start")
		self._r_busy = RegisterField("busy", access_bus=READ_ONLY, access_dev=WRITE_ONLY)
		self._r_size = RegisterField("size", bits_for(self.depth), reset=self.depth)
		
		# data interface, in signal clock domain
		self.value = Signal(self.width)

	def get_registers(self):
		return [self._r_start, self._r_busy, self._r_size]

	def get_memories(self):
		return [self._mem]
		
	def build_fragment(self):
		# register controls transferred to signal clock domain
		start = Signal()
		done = Signal()
		size = Signal(bits_for(self.depth))
		self._ps_start = PulseSynchronizer("sys", "signal")
		self.comb += [
			self._ps_start.i.eq(self._r_start.re),
			start.eq(self._ps_start.o)
		]
		self._ps_done = PulseSynchronizer("signal", "sys")
		self.comb += self._ps_done.i.eq(done)
		self.sync += [
			If(self._r_start.re,
				self._r_busy.field.w.eq(1)
			).Elif(self._ps_done.o,
				self._r_busy.field.w.eq(0)
			)
		]
		self.specials += MultiReg(self._r_size.field.r, "sys", size, "signal")
		#
		active = Signal()
		write_address = Signal(max=self.depth)
		mem_port = self._mem.get_port(write_capable=True, clock_domain="signal")
		self.comb += [
			mem_port.adr.eq(write_address),
			mem_port.dat_w.eq(self.value),
			mem_port.we.eq(active)
		]
		self.sync.signal += [
			done.eq(0),
			If(active,
				write_address.eq(write_address + 1),
				If(write_address == size - 1, 
					active.eq(0),
					done.eq(1)
				)
			).Else(
				If(start, active.eq(1))
			)
		]
		
class WaveformCollector(FModule):
	def __init__(self, baseapp):
		adc_pins = baseapp.mplat.request("ti_adc")
		width = 2*len(adc_pins.dat_a_p)

		self._wm_a = WaveformMemoryIn(1024, width)
		self._wm_b = WaveformMemoryIn(1024, width)
		self._adc = ADC(adc_pins)

		registers = regprefix("a_", self._wm_a.get_registers()) \
			+ regprefix("b_", self._wm_b.get_registers())
		memories = memprefix("a_", self._wm_a.get_memories()) \
			+ memprefix("b_", self._wm_b.get_memories())
		baseapp.csrs.request("wc", UID_WAVEFORM_COLLECTOR, *registers, memories=memories)

	def build_fragment(self):
		self.comb += [
			self._wm_a.value.eq(self._adc.a),
			self._wm_b.value.eq(self._adc.b)
		]

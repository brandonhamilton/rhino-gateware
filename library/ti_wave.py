from migen.fhdl.structure import *
from migen.fhdl.specials import Memory
from migen.fhdl.module import Module
from migen.bank.description import *
from migen.genlib.cdc import MultiReg, PulseSynchronizer

from library.uid import UID_WAVEFORM_GENERATOR, UID_WAVEFORM_COLLECTOR
from library.ti_io import DAC, DAC2X, ADC

class WaveformMemoryOut(Module, AutoReg):
	def __init__(self, depth, width, spc):
		self.depth = depth
		self.width = width
		self.spc = spc

		self.specials._mem_i = Memory(self.width, self.depth)
		self.specials._mem_q = Memory(self.width, self.depth)
		
		# registers are in the system clock domain
		self._r_playback_en = RegisterField()
		self._r_size = RegisterField(bits_for(self.depth), reset=self.depth)
		self._r_mult = RegisterField(bits_for(self.depth), reset=1)
		
		# data interface, in signal clock domain
		for i in range(self.spc):
			name = "value_i" + str(i)
			setattr(self, name, Signal(self.width, name=name))
			name = "value_q" + str(i)
			setattr(self, name, Signal(self.width, name=name))

		###

		# register data transferred to signal clock domain
		play_en = Signal()
		size = Signal(bits_for(self.depth))
		mult = Signal(bits_for(self.depth))
		self.specials += {
			MultiReg(self._r_playback_en.field.r, play_en, "signal"),
			MultiReg(self._r_size.field.r, size, "signal"),
			MultiReg(self._r_mult.field.r, mult, "signal"),
		}
		#
		mem_ports = [(self._mem_i.get_port(clock_domain="signal"),
			self._mem_q.get_port(clock_domain="signal"))
			for i in range(self.spc)]
		for n, (port_i, port_q) in enumerate(mem_ports):
			nbits = bits_for(self.depth-1)+1
			mem_a = Signal(nbits)
			v_mem_a = Signal(nbits, variable=True)
			self.sync.signal += [
				v_mem_a.eq(mem_a),
				If(~play_en,
					v_mem_a.eq(n*mult)
				).Else(
					v_mem_a.eq(v_mem_a + self.spc*mult)
				),
				If(v_mem_a >= size,
					v_mem_a.eq(v_mem_a - size)
				),
				mem_a.eq(v_mem_a),
				getattr(self, "value_i" + str(n)).eq(port_i.dat_r),
				getattr(self, "value_q" + str(n)).eq(port_q.dat_r)
			]
			self.comb += [
				port_i.adr.eq(mem_a),
				port_q.adr.eq(mem_a)
			]

class WaveformGenerator(Module):
	def __init__(self, baseapp):
		dac_pins = baseapp.mplat.request("ti_dac")
		width = 2*len(dac_pins.dat_p)
		
		_double_dac = baseapp.double_dac
		spc = 2 if _double_dac else 1
		dac_class = DAC2X if _double_dac else DAC
		
		self.submodules._wm = WaveformMemoryOut(1024, width, spc)
		self.submodules._dac = dac_class(dac_pins, baseapp.crg.dacio_strb)

		registers = self._wm.get_registers() + self._dac.get_registers()
		baseapp.csrs.request("wg", UID_WAVEFORM_GENERATOR,
			*registers, memories=self._wm.get_memories())
	
		###
	
		if _double_dac:
			self.comb += [
				self._dac.i0.eq(self._wm.value_i0),
				self._dac.q0.eq(self._wm.value_q0),
				self._dac.i1.eq(self._wm.value_i1),
				self._dac.q1.eq(self._wm.value_q1)
			]
		else:
			self.comb += [
				self._dac.i.eq(self._wm.value_i0),
				self._dac.q.eq(self._wm.value_q0)
			]

class WaveformMemoryIn(Module, AutoReg):
	def __init__(self, depth, width):
		self.depth = depth
		self.width = width

		self.specials._mem = Memory(self.width, self.depth)
		self._mem.bus_read_only = True
		
		# registers are in the system clock domain
		self._r_start = RegisterRaw()
		self._r_busy = RegisterField(1, READ_ONLY, WRITE_ONLY)
		self._r_size = RegisterField(bits_for(self.depth), reset=self.depth)
		
		# data interface, in signal clock domain
		self.value = Signal(self.width)

		###

		# register controls transferred to signal clock domain
		start = Signal()
		done = Signal()
		size = Signal(bits_for(self.depth))
		self.submodules._ps_start = PulseSynchronizer("sys", "signal")
		self.comb += [
			self._ps_start.i.eq(self._r_start.re),
			start.eq(self._ps_start.o)
		]
		self.submodules._ps_done = PulseSynchronizer("signal", "sys")
		self.comb += self._ps_done.i.eq(done)
		self.sync += [
			If(self._r_start.re,
				self._r_busy.field.w.eq(1)
			).Elif(self._ps_done.o,
				self._r_busy.field.w.eq(0)
			)
		]
		self.specials += MultiReg(self._r_size.field.r, size, "signal")
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
			write_address.eq(0),
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
		
class WaveformCollector(Module):
	def __init__(self, baseapp):
		adc_pins = baseapp.mplat.request("ti_adc")
		width = 2*len(adc_pins.dat_a_p)

		self.submodules._wm = WaveformMemoryIn(1024, 2*width)
		self.submodules._adc = ADC(adc_pins)

		baseapp.csrs.request("wc", UID_WAVEFORM_COLLECTOR, 
			*self._wm.get_registers(), memories=self._wm.get_memories())

		self.comb += self._wm.value.eq(Cat(self._adc.a, self._adc.b))

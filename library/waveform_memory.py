from migen.fhdl.std import *
from migen.bank.description import *
from migen.genlib.cdc import MultiReg, PulseSynchronizer

class WaveformMemoryOut(Module, AutoCSR):
	def __init__(self, depth, width, spc):
		self.specials._mem_i = Memory(width, depth)
		self.specials._mem_q = Memory(width, depth)
		
		# registers are in the system clock domain
		self._r_playback_en = CSRStorage()
		self._r_size = CSRStorage(bits_for(depth), reset=depth)
		self._r_mult = CSRStorage(bits_for(depth), reset=1)
		
		# data interface, in signal clock domain
		for i in range(spc):
			name = "value_i" + str(i)
			setattr(self, name, Signal(width, name=name))
			name = "value_q" + str(i)
			setattr(self, name, Signal(width, name=name))

		###

		# register data transferred to signal clock domain
		play_en = Signal()
		size = Signal(bits_for(depth))
		mult = Signal(bits_for(depth))
		self.specials += {
			MultiReg(self._r_playback_en.storage, play_en, "signal"),
			MultiReg(self._r_size.storage, size, "signal"),
			MultiReg(self._r_mult.storage, mult, "signal"),
		}
		#
		for n in range(spc):
			port_i = self._mem_i.get_port(clock_domain="signal")
			port_q = self._mem_q.get_port(clock_domain="signal")
			self.specials += port_i, port_q
			nbits = bits_for(depth-1)+1
			mem_a = Signal(nbits)
			next_mem_a0 = Signal(nbits)
			next_mem_a = Signal(nbits)
			self.comb += [
				If(~play_en,
					next_mem_a0.eq(n*mult)
				).Else(
					next_mem_a0.eq(mem_a + spc*mult)
				),
				If(next_mem_a0 >= size,
					next_mem_a.eq(next_mem_a0 - size)
				).Else(
					next_mem_a.eq(next_mem_a0)
				)
			]
			self.sync.signal += [
				mem_a.eq(next_mem_a),
				getattr(self, "value_i" + str(n)).eq(port_i.dat_r),
				getattr(self, "value_q" + str(n)).eq(port_q.dat_r)
			]
			self.comb += [
				port_i.adr.eq(mem_a),
				port_q.adr.eq(mem_a)
			]

class WaveformMemoryIn(Module, AutoCSR):
	def __init__(self, depth, width):
		self.specials._mem = Memory(width, depth)
		self._mem.bus_read_only = True
		
		# registers are in the system clock domain
		self._r_start = CSR()
		self._r_busy = CSRStatus()
		self._r_size = CSRStorage(bits_for(depth), reset=depth)
		
		# data interface, in signal clock domain
		self.value = Signal(width)

		###

		# register controls transferred to signal clock domain
		start = Signal()
		done = Signal()
		size = Signal(bits_for(depth))
		self.submodules._ps_start = PulseSynchronizer("sys", "signal")
		self.comb += [
			self._ps_start.i.eq(self._r_start.re),
			start.eq(self._ps_start.o)
		]
		self.submodules._ps_done = PulseSynchronizer("signal", "sys")
		self.comb += self._ps_done.i.eq(done)
		self.sync += [
			If(self._r_start.re,
				self._r_busy.status.eq(1)
			).Elif(self._ps_done.o,
				self._r_busy.status.eq(0)
			)
		]
		self.specials += MultiReg(self._r_size.storage, size, "signal")
		#
		active = Signal()
		write_address = Signal(max=depth)
		mem_port = self._mem.get_port(write_capable=True, clock_domain="signal")
		self.specials += mem_port
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

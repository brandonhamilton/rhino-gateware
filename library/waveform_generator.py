from migen.fhdl.structure import *
from migen.bank.description import *
from migen.flow.actor import *
from migen.genlib.fsm import FSM

MODE_DISABLED = 0
MODE_LOAD = 1
MODE_PLAYBACK = 2

class WaveformGenerator(Actor):
	def __init__(self, depth, width=16, spc=1):
		self.depth = depth
		self.width = width
		self.spc = spc
		
		self._mode = RegisterField("mode", 2)
		self._busy = RegisterField("busy", access_bus=READ_ONLY, access_dev=WRITE_ONLY)
		self._size = RegisterField("size", bits_for(self.depth), reset=self.depth)
		self._mult = RegisterField("mult", bits_for(self.depth), reset=1)
		self._data_ins = [RegisterField("data_in" + str(i), self.width) for i in range(self.spc)]
		self._shift_data = RegisterRaw("shift_data")
		
		layout = [("value" + str(i), self.width) for i in range(self.spc)]
		Actor.__init__(self, ("sample", Source, layout))

	def get_registers(self):
		return [self._mode, self._busy,
			self._size, self._mult] \
			+ self._data_ins + [self._shift_data]
		
	def get_fragment(self):
		# memory
		mem = Memory(self.width, self.depth)
		mem_ports = [mem.get_port(write_capable=True, has_re=True) 
			for i in range(self.spc)]
		
		# address generator
		adr_reset = Signal()
		adr_inc_1 = Signal()
		adr_inc_mult = Signal()
		sync = []
		for n, port in enumerate(mem_ports):
			v_mem_a = Signal(bits_for(self.depth-1)+1, variable=True)
			sync += [
				v_mem_a.eq(port.adr),
				If(adr_reset,
					v_mem_a.eq(n*self._mult.field.r)
				).Elif(adr_inc_1,
					v_mem_a.eq(v_mem_a + self.spc)
				).Elif(adr_inc_mult,
					v_mem_a.eq(v_mem_a + self.spc*self._mult.field.r)
				),
				If(v_mem_a >= self._size.field.r,
					v_mem_a.eq(v_mem_a - self._size.field.r)
				),
				port.adr.eq(v_mem_a)
			]
		
		# glue
		mem_re = Signal()
		mem_we = Signal()
		mem_dat_ws = [port.dat_w for port in mem_ports]
		data_in_rs = [r.field.r for r in self._data_ins]
		comb = [
			Cat(*mem_dat_ws).eq(Cat(*data_in_rs)),
			self._busy.field.w.eq(self.busy)
		]
		for i, port in enumerate(mem_ports):
			comb += [
				port.re.eq(mem_re),
				port.we.eq(mem_we),
				getattr(self.token("sample"), "value" + str(i)).eq(port.dat_r)
			]
		
		# control
		fsm = FSM("IDLE", "LOAD", "FLUSH", "PLAYBACK")
		fsm.act(fsm.IDLE,
			self.busy.eq(0),
			adr_reset.eq(1),
			If(self._mode.field.r == MODE_LOAD, fsm.next_state(fsm.LOAD)),
			If(self._mode.field.r == MODE_PLAYBACK, fsm.next_state(fsm.FLUSH))
		)
		fsm.act(fsm.LOAD,
			self.busy.eq(0),
			If(self._shift_data.re,
				mem_we.eq(1),
				adr_inc_1.eq(1)
			),
			If(self._mode.field.r != MODE_LOAD, fsm.next_state(fsm.IDLE))
		)
		fsm.act(fsm.FLUSH,
			self.busy.eq(1),
			mem_re.eq(1),
			adr_inc_mult.eq(1),
			fsm.next_state(fsm.PLAYBACK)
		)
		fsm.act(fsm.PLAYBACK,
			self.busy.eq(1),
			self.endpoints["sample"].stb.eq(1),
			If(self.endpoints["sample"].ack,
				adr_inc_mult.eq(1),
				mem_re.eq(1),
				If(self._mode.field.r != MODE_PLAYBACK, fsm.next_state(fsm.IDLE))
			)
		)
		
		return fsm.get_fragment() \
			+ Fragment(comb, sync, memories=[mem])

from migen.fhdl.structure import *
from migen.bank.description import *
from migen.flow.actor import *
from migen.corelogic.fsm import FSM

MODE_DISABLED = 0
MODE_LOAD = 1
MODE_PLAYBACK = 2

class WaveformGenerator(Actor):
	def __init__(self, depth, width=16):
		self.depth = depth
		self.width = width
		
		self._mode = RegisterField("mode")
		self._busy = RegisterField("busy", access_bus=READ_ONLY, access_dev=WRITE_ONLY)
		self._size = RegisterField("size", bits_for(self.depth))
		self._mult = RegisterField("mult", bits_for(self.depth), reset=1)
		self._data_in = RegisterField("data_in", self.width)
		self._shift_data = RegisterField("shift_data", access_bus=WRITE_ONLY)
		
		super().__init__(("sample", Source, [("value", BV(self.width))]))

	def get_registers(self):
		return [self._mode, self._busy,
			self._size, self._mult,
			self._data_in, self._shift_data]
		
	def get_fragment(self):
		# memory
		mem_a = Signal(BV(bits_for(self.depth-1)))
		mem_re = Signal()
		mem_dr = Signal(BV(self.width))
		mem_we = Signal()
		mem_dw = Signal(BV(self.width))
		mem = Memory(self.width, self.depth,
			MemoryPort(mem_a, mem_dr, mem_we, mem_dw, re=mem_re))
		
		# address generator
		v_mem_a = Signal(BV(bits_for(self.depth-1)), variable=True)
		adr_reset = Signal()
		adr_inc_1 = Signal()
		adr_inc_mult = Signal()
		sync = [
			If(adr_reset,
				v_mem_a.eq(0)
			).Elif(adr_inc_1,
				v_mem_a.eq(mem_a + 1)
			).Elif(adr_inc_mult,
				v_mem_a.eq(mem_a + self._mult.field.r)
			)
			If(v_mem_a >= self._size.field.r,
				v_mem_a.eq(v_mem_a - self._size.field.r)
			)
			mem_a.eq(v_mem_a)
		]
		
		# glue
		comb = [
			self.token("sample").value.eq(mem_dr),
			mem_dw.eq(self._data_in.field.r),
			self._busy.field.w.eq(self.busy)
		]
		
		# control
		fsm = FSM("IDLE", "LOAD", "FLUSH", "PLAYBACK")
		fsm.act(fsm.IDLE,
			self.busy.eq(0),
			adr_reset.eq(1),
			If(self._mode.field.r == MODE_LOAD, fsm.next_state(fsm.LOAD)),
			If(self._mode.field.r == MODE_PLAYBACK, fsm.next_state(fsm.PLAYBACK))
		)
		fsm.act(fsm.LOAD,
			self.busy.eq(0),
			If(self._shift_data.field.re,
				mem_we.eq(1),
				adr_inc_1.eq(1)
			),
			If(self._mode.field.r != MODE_LOAD, fsm.next_state(fsm.IDLE))
		)
		fsm.act(fsm.FLUSH,
			self.busy.eq(1),
			mem_re.eq(1),
			fsm.next_state(fsm.PLAYBACK)
		)
		fsm.act(fsm.PLAYBACK,
			self.busy.eq(1),
			self.endpoints["sample"].stb.eq(1),
			If(self.endpoints["sample"].ack,
				adr_inc_mult.eq(1),
				mem_re.eq(1),
				If(self._mode.field.r != MODE_LOAD, fsm.next_state(fsm.IDLE))
			)
		)
		
		return fsm.get_fragment() \
			+ Fragment(comb, sync, memories=[mem])

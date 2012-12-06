from migen.fhdl.structure import *
from migen.flow.actor import *
from migen.bank.description import *
from migen.corelogic.fsm import FSM

# 6-bit RF digital attenuator
class PE43602Driver(Actor):
	def __init__(self, cycle_bits=8):
		self.d = Signal()
		self.clk = Signal()
		self.le = Signal()
		
		self._cycle_bits = cycle_bits
		
		self._pos_end_cycle = RegisterField("pos_end_cycle", self._cycle_bits, reset=20)
		self._pos_data = RegisterField("pos_data", self._cycle_bits, reset=0)
		self._pos_le_high = RegisterField("pos_le_high", self._cycle_bits, reset=5)
		self._pos_le_low = RegisterField("pos_le_low", self._cycle_bits, reset=15)
		
		super().__init__(("attn", Sink, [("attn", 8)]))
	
	def get_registers(self):
		return [self._pos_end_cycle, self._pos_data, self._pos_le_high, self._pos_le_low]
	
	def get_fragment(self):
		# cycle counter and events
		cycle_counter = Signal(self._cycle_bits)
		cycle_counter_reset = Signal()
		eoc = Signal()
		comb = [
			eoc.eq(cycle_counter == self._pos_end_cycle.field.r)
		]
		sync = [
			If(eoc | cycle_counter_reset,
				cycle_counter.eq(0)
			).Else(
				cycle_counter.eq(cycle_counter + 1)
			)
		]
		
		ev_clk_high = Signal()
		ev_clk_low = Signal()
		ev_data = Signal()
		comb += [
			ev_clk_high.eq(cycle_counter == (self._pos_end_cycle.field.r >> 1)),
			ev_clk_low.eq(cycle_counter == self._pos_end_cycle.field.r),
			ev_data.eq(cycle_counter == self._pos_data.field.r)
		]
		
		le_counter = Signal(self._cycle_bits)
		le_counter_reset = Signal()
		sync += [
			If(le_counter_reset,
				le_counter.eq(0)
			).Else(
				le_counter.eq(le_counter + 1)
			)
		]
		
		ev_le_high = Signal()
		ev_le_low = Signal()
		comb += [
			ev_le_high.eq(le_counter == self._pos_le_high.field.r),
			ev_le_low.eq(le_counter == self._pos_le_low.field.r)
		]
		
		# data
		sr = Signal(8)
		sr_load = Signal()
		sr_shift = Signal()
		remaining_data = Signal(4)
		sync += [
			If(sr_load,
				sr.eq(self.token("attn").attn),
				remaining_data.eq(8)
			).Elif(sr_shift,
				sr.eq(sr[1:]),
				self.d.eq(sr[0]),
				remaining_data.eq(remaining_data-1)
			)
		]
		
		# clock
		clk_p = Signal()
		clk_high = Signal()
		clk_low = Signal()
		sync += [
			If(clk_high,
				clk_p.eq(1)
			).Elif(clk_low,
				clk_p.eq(0)
			),
			self.clk.eq(clk_p)
		]
		
		# LE
		le_p = Signal()
		le_high = Signal()
		le_low = Signal()
		sync += [
			If(le_high,
				le_p.eq(1)
			).Elif(le_low,
				le_p.eq(0)
			),
			self.le.eq(le_p)
		]
		
		# control FSM
		fsm = FSM("WAIT_DATA", "TRANSFER_DATA", "LE")
		
		fsm.act(fsm.WAIT_DATA,
			cycle_counter_reset.eq(1),
			le_counter_reset.eq(1),
			sr_load.eq(1),
			self.endpoints["attn"].ack.eq(1),
			If(self.endpoints["attn"].stb,
				fsm.next_state(fsm.TRANSFER_DATA)
			)
		)
		fsm.act(fsm.TRANSFER_DATA,
			le_counter_reset.eq(1),
			self.busy.eq(1),
			clk_high.eq(ev_clk_high),
			clk_low.eq(ev_clk_low),
			sr_shift.eq(ev_data),
			If(eoc & (remaining_data == 0),
				fsm.next_state(fsm.LE)
			)
		)
		fsm.act(fsm.LE,
			cycle_counter_reset.eq(1),
			self.busy.eq(1),
			cycle_counter_reset.eq(1),
			le_high.eq(ev_le_high),
			le_low.eq(ev_le_low),
			If(ev_le_low,
				fsm.next_state(fsm.WAIT_DATA)
			)
		)
		
		return Fragment(comb, sync) + fsm.get_fragment()

# IQ Modulator with Synthesizer/VCO
class RFMD2081Driver:
	def __init__(self):
		pass
	
	def get_registers(self):
		return []
	
	def get_fragment(self):
		return Fragment()

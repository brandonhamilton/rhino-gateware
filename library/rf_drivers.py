from migen.fhdl.structure import *
from migen.corelogic.fsm import FSM

# 6-bit RF digital attenuator
class PE4302Driver(Actor):
	def __init__(self, cycle_bits=8):
		self.d = Signal()
		self.clk = Signal()
		self.le = Signal()
		
		self._cycle_bits = cycle_bits
		
		self._pos_end_cycle = RegisterField("pos_end_cycle", self._cycle_bits)
		self._pos_data = RegisterField("pos_data", self._cycle_bits)
		self._pos_le_high = RegisterField("le_delay", self._cycle_bits)
		self._pos_le_low = RegisterField("le_width", self._cycle_bits)
		
		super().__init__(("attn", Source, [("attn", 8)]))
	
	def get_registers(self):
		return [self._pos_end_cycle, self._pos_data, self._le_delay, self._le_width]
	
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
				cycle_counter.eq(0),
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
		sync += [
			If(ev_clk_high,
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
		sync += [
			If(sr_load,
				sr.eq(self.token("attn").attn)
			).Elif(sr_shift,
				sr.eq(sr[1:])
			),
			self.d.eq(sr_shift[0])
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
			sr_load.eq(1),
			self.endpoints["attn"].ack.eq(1),
			If(self.endpoints["attn"].stb,
				fsm.next_state(fsm.TRANSFER_DATA)
			)
		)
		fsm.act(fsm.TRANSFER_DATA,
			self.busy.eq(1),
			clk_high.eq(ev_clk_high),
			clk_low.eq(ev_clk_low),
			sr_shift.eq(ev_data),
			If(eoc & (remaining_data == 0),
				fsm.next_state(fsm.LE)
			)
		)
		fsm.act(fsm.LE,
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

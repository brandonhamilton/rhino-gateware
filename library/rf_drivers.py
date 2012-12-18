from migen.fhdl.structure import *
from migen.fhdl.tools import bitreverse
from migen.flow.actor import *
from migen.bank.description import *
from migen.corelogic.fsm import FSM

class SerialDataWriter:
	def __init__(self, cycle_bits, data_bits, extra_fsm_states=[]):
		self.cycle_bits = cycle_bits
		self.data_bits = data_bits
		
		# I/O signals
		self.d = Signal()
		self.clk = Signal()
		
		# control signals
		self.pds = Signal()
		self.pdi = Signal(self.data_bits)
		
		self.eoc = Signal()
		self.ev_clk_high = Signal()
		self.ev_clk_low = Signal()
		self.ev_data = Signal()
		
		# FSM
		fsm_states = ["WAIT_DATA", "TRANSFER_DATA"] + extra_fsm_states
		self.fsm = FSM(*fsm_states)
		self.end_action = [self.fsm.next_state(self.fsm.WAIT_DATA)]
		
		# registers
		self._pos_end_cycle = RegisterField("pos_end_cycle", self.cycle_bits, reset=20)
		self._pos_data = RegisterField("pos_data", self.cycle_bits, reset=0)
	
	def get_registers(self):
		return [self._pos_end_cycle, self._pos_data]
	
	def get_fragment(self):
		# cycle counter and events
		cycle_counter = Signal(self.cycle_bits)
		cycle_counter_reset = Signal()
		comb = [
			self.eoc.eq(cycle_counter == self._pos_end_cycle.field.r)
		]
		sync = [
			If(self.eoc | cycle_counter_reset,
				cycle_counter.eq(0)
			).Else(
				cycle_counter.eq(cycle_counter + 1)
			)
		]
		
		comb += [
			self.ev_clk_high.eq(cycle_counter == (self._pos_end_cycle.field.r >> 1)),
			self.ev_clk_low.eq(cycle_counter == self._pos_end_cycle.field.r),
			self.ev_data.eq(cycle_counter == self._pos_data.field.r)
		]
		
		# data
		sr = Signal(self.data_bits)
		sr_load = Signal()
		sr_shift = Signal()
		remaining_data = Signal(max=self.data_bits+1)
		sync += [
			If(sr_load,
				sr.eq(self.pdi),
				remaining_data.eq(self.data_bits)
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
		
		# control FSM
		self.fsm.act(self.fsm.WAIT_DATA,
			cycle_counter_reset.eq(1),
			sr_load.eq(1),
			If(self.pds,
				self.fsm.next_state(self.fsm.TRANSFER_DATA)
			)
		)
		self.fsm.act(self.fsm.TRANSFER_DATA,
			clk_high.eq(self.ev_clk_high),
			clk_low.eq(self.ev_clk_low),
			sr_shift.eq(self.ev_data),
			If(self.eoc & (remaining_data == 0),
				*self.end_action
			)
		)
		
		return Fragment(comb, sync) + self.fsm.get_fragment()

# 6-bit RF digital attenuator
class PE43602Driver(Actor):
	def __init__(self, cycle_bits=8):
		self._sdw = SerialDataWriter(cycle_bits, 8, ["LE"])
		self._sdw.end_action = [self._sdw.fsm.next_state(self._sdw.fsm.LE)]
		
		self.d = self._sdw.d
		self.clk = self._sdw.clk
		self.le = Signal()
		
		self._pos_le_high = RegisterField("pos_le_high", self._sdw.cycle_bits, reset=5)
		self._pos_le_low = RegisterField("pos_le_low", self._sdw.cycle_bits, reset=15)
		
		Actor.__init__(self, ("program", Sink, [("attn", 8)]))
	
	def get_registers(self):
		return self._sdw.get_registers() + [self._pos_le_high, self._pos_le_low]
	
	def get_fragment(self):
		comb = [
			self._sdw.pds.eq(self.endpoints["program"].stb),
			self._sdw.pdi.eq(self.token("program").attn)
		]
		
		# LE counter
		le_counter = Signal(self._sdw.cycle_bits)
		le_counter_reset = Signal()
		sync = [
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
		
		# complete FSM
		fsm = self._sdw.fsm
		fsm.act(fsm.WAIT_DATA,
			le_counter_reset.eq(1),
			self.endpoints["program"].ack.eq(1)
		)
		fsm.act(fsm.TRANSFER_DATA,
			le_counter_reset.eq(1),
			self.busy.eq(1)
		)
		fsm.act(fsm.LE,
			self.busy.eq(1),
			le_high.eq(ev_le_high),
			le_low.eq(ev_le_low),
			If(ev_le_low,
				fsm.next_state(fsm.WAIT_DATA)
			)
		)
		
		return Fragment(comb, sync) + self._sdw.get_fragment()

class SPIWriter:
	def __init__(self, cycle_bits, data_bits):
		self.sdw = SerialDataWriter(cycle_bits, data_bits, ["CSN_HI"])
		self.sdw.end_action = [self.sdw.fsm.next_state(self.sdw.fsm.CSN_HI)]
		
		self.mosi = Signal()
		self.miso = Signal()
		self.csn = Signal(reset=1)
		self.clk = Signal()
		
		self.spi_busy = Signal()
		self.miso_synced = Signal()
		
		# bitbang control
		self._bb_enable = RegisterField("bb_enable")
		self._bb_mosi = Field("mosi")
		self._bb_clk = Field("clk")
		self._bb_csn = Field("csn", reset=1)
		self._bb_out = RegisterFields("bb_out", [self._bb_mosi, self._bb_csn, self._bb_clk])
		self._bb_miso = RegisterField("bb_miso", access_dev=WRITE_ONLY, access_bus=READ_ONLY)
		
	def get_registers(self):
		return [self._bb_enable, self._bb_out, self._bb_miso] + self.sdw.get_registers()
	
	def get_fragment(self):
		# CS_N
		csn = Signal()
		csn_p = Signal()
		csn_high = Signal()
		csn_low = Signal()
		sync = [
			If(csn_high,
				csn_p.eq(1)
			).Elif(csn_low,
				csn_p.eq(0)
			),
			csn.eq(csn_p)
		]
		
		# bitbang
		miso_r1 = Signal()
		sync += [
			miso_r1.eq(self.miso),
			self.miso_synced.eq(miso_r1)
		]
		comb = [
			If(self._bb_enable.field.r,
				self.mosi.eq(self._bb_mosi.r),
				self.clk.eq(self._bb_clk.r),
				self.csn.eq(self._bb_csn.r)
			).Else(
				self.mosi.eq(self.sdw.d),
				self.clk.eq(self.sdw.clk),
				self.csn.eq(csn)
			),
			self._bb_miso.field.w.eq(self.miso_synced)
		]
		
		# complete FSM
		fsm = self.sdw.fsm
		fsm.act(fsm.TRANSFER_DATA,
			If(self.sdw.ev_data,
				# ENX shares the data timing
				csn_low.eq(1)
			),
			self.spi_busy.eq(1)
		)
		fsm.act(fsm.CSN_HI,
			If(self.sdw.ev_data,
				csn_high.eq(1)
			),
			If(self.sdw.eoc,
				fsm.next_state(fsm.WAIT_DATA)
			),
			self.spi_busy.eq(1)
		)
		
		return Fragment(comb, sync) + self.sdw.get_fragment()

		
# RFMD's second-generation integrated synthesizer/mixer/modulator devices, e.g.
# RFMD2081 IQ Modulator with Synthesizer/VCO
# RFFC5071 Wideband Synthesizer/VCO with Integrated Mixer
class RFMDISMMDriver(SPIWriter, Actor):
	def __init__(self, cycle_bits=8):
		SPIWriter.__init__(self, cycle_bits, 25)
		Actor.__init__(self, ("program", Sink, [("addr", 7), ("data", 16)]))
	
	def get_fragment(self):
		word = Signal(25)
		comb = [
			self.sdw.pds.eq(self.endpoints["program"].stb),
			word.eq(Cat(self.token("program").data, self.token("program").addr)),
			self.sdw.pdi.eq(bitreverse(word)),
			self.busy.eq(self.spi_busy)
		]
		self.sdw.fsm.act(self.sdw.fsm.WAIT_DATA,
			self.endpoints["program"].ack.eq(1)
		)
		return SPIWriter.get_fragment(self) + Fragment(comb)

# Dual variable gain amplifier
class LMH6521(SPIWriter, Actor):
	def __init__(self, cycle_bits=8):
		SPIWriter.__init__(self, cycle_bits, 16)
		Actor.__init__(self, ("program", Sink, [("channel", 1), ("gain", 8)]))
	
	def get_fragment(self):
		word = Signal(16)
		comb = [
			self.sdw.pds.eq(self.endpoints["program"].stb),
			word.eq(Cat(self.token("program").gain, self.token("program").channel)),
			self.sdw.pdi.eq(bitreverse(word)),
			self.busy.eq(self.spi_busy)
		]
		self.sdw.fsm.act(self.sdw.fsm.WAIT_DATA,
			self.endpoints["program"].ack.eq(1)
		)
		return SPIWriter.get_fragment(self) + Fragment(comb)

from migen.fhdl.structure import *
from migen.fhdl.specials import TSTriple
from migen.fhdl.tools import bitreverse
from migen.flow.actor import *
from migen.bank.description import *
from migen.genlib.fsm import FSM

class I2CDataWriter:
	def __init__(self, cycle_bits, data_bits):
		self.cycle_bits = cycle_bits
		self.data_bits = data_bits
		
		# I/O signals
		self.d = Signal(reset=1)
		self.clk = Signal(reset=1)
		
		# control signals
		self.pds = Signal()
		self.pdi = Signal(self.data_bits)
		
		self.clk_high = Signal()
		self.clk_low = Signal()
		
		self.busy = Signal()
		self.eoc = Signal()
		self.ev_clk_high = Signal()
		self.ev_clk_low = Signal()
		self.ev_data = Signal()
		self.ev_start = Signal()
		self.ev_stop_low = Signal()
		self.ev_stop_high = Signal()
		
		# FSM
		self.fsm = FSM("WAIT_DATA", "START_CONDITION", "TRANSFER_DATA", "ACK", "STOP_CONDITION")
		
		# registers
		self._pos_end_cycle = RegisterField("pos_end_cycle", self.cycle_bits, reset=240)
		self._pos_clk_high = RegisterField("pos_clk_high", self.cycle_bits, reset=140)
		self._pos_data = RegisterField("pos_data", self.cycle_bits, reset=70)
		self._pos_start = RegisterField("pos_start", self.cycle_bits, reset=170)
		self._pos_stop_low = RegisterField("pos_stop_low", self.cycle_bits, reset=70)
		self._pos_stop_high = RegisterField("pos_stop_high", self.cycle_bits, reset=210)
		
	def get_registers(self):
		return [self._pos_end_cycle,
			self._pos_clk_high,
			self._pos_data,
			self._pos_start,
			self._pos_stop_low,
			self._pos_stop_high]
	
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
			self.ev_clk_high.eq(cycle_counter == self._pos_clk_high.field.r),
			self.ev_clk_low.eq(cycle_counter == self._pos_end_cycle.field.r),
			self.ev_data.eq(cycle_counter == self._pos_data.field.r),
			self.ev_start.eq(cycle_counter == self._pos_start.field.r),
			self.ev_stop_low.eq(cycle_counter == self._pos_stop_low.field.r),
			self.ev_stop_high.eq(cycle_counter == self._pos_stop_high.field.r)
		]
		
		# data
		sr = Signal(self.data_bits)
		sr_load = Signal()
		sr_shift = Signal()
		data_start = Signal()
		data_stop_low = Signal()
		data_stop_high = Signal()
		remaining_data = Signal(max=self.data_bits+1)
		sync += [
			If(sr_load,
				sr.eq(self.pdi),
				remaining_data.eq(self.data_bits)
			).Elif(sr_shift,
				sr.eq(sr[1:]),
				self.d.eq(sr[0]),
				remaining_data.eq(remaining_data-1)
			).Elif(data_start,
				self.d.eq(0)
			).Elif(data_stop_low,
				self.d.eq(0)
			).Elif(data_stop_high,
				self.d.eq(1)
			)
		]
		
		# clock
		clk_p = Signal(reset=1)
		sync += [
			If(self.clk_high,
				clk_p.eq(1)
			).Elif(self.clk_low,
				clk_p.eq(0)
			),
			self.clk.eq(clk_p)
		]
		
		# control FSM
		self.fsm.act(self.fsm.WAIT_DATA,
			cycle_counter_reset.eq(1),
			sr_load.eq(1),
			If(self.pds,
				self.fsm.next_state(self.fsm.START_CONDITION)
			)
		)
		self.fsm.act(self.fsm.START_CONDITION,
			self.busy.eq(1),
			self.clk_high.eq(self.ev_clk_high),
			self.clk_low.eq(self.ev_clk_low),
			data_start.eq(self.ev_start),
			If(self.eoc,
				self.fsm.next_state(self.fsm.TRANSFER_DATA)
			)
		)
		self.fsm.act(self.fsm.TRANSFER_DATA,
			self.busy.eq(1),
			self.clk_high.eq(self.ev_clk_high),
			self.clk_low.eq(self.ev_clk_low),
			sr_shift.eq(self.ev_data),
			If(self.eoc & (remaining_data[0:3] == 0),
				self.fsm.next_state(self.fsm.ACK)
			)
		)
		self.fsm.act(self.fsm.ACK,
			self.busy.eq(1),
			self.clk_high.eq(self.ev_clk_high),
			self.clk_low.eq(self.ev_clk_low),
			If(self.eoc,
				If(remaining_data == 0,
					self.fsm.next_state(self.fsm.STOP_CONDITION)
				).Else(self.fsm.next_state(self.fsm.TRANSFER_DATA))
			)
		)
		self.fsm.act(self.fsm.STOP_CONDITION,
			self.busy.eq(1),
			self.clk_high.eq(self.ev_clk_high),
			data_stop_low.eq(self.ev_stop_low),
			data_stop_high.eq(self.ev_stop_high),
			If(self.eoc,
				self.fsm.next_state(self.fsm.WAIT_DATA)
			)
		)
		
		return Fragment(comb, sync) + self.fsm.get_fragment()

class BBI2CDataWriter(I2CDataWriter):
	def __init__(self, *args, **kwargs):
		self.idw = I2CDataWriter(*args, **kwargs)

		self.sda = TSTriple(reset_o=1, reset_oe=1)
		self.scl = Signal()

		self._bb_enable = RegisterField("bb_enable")
		self._bb_sda_oe = Field("sda_oe")
		self._bb_sda_o = Field("sda_o")
		self._bb_scl = Field("scl")
		self._bb_out = RegisterFields("bb_out", [self._bb_sda_oe, self._bb_sda_o, self._bb_scl])
		self._bb_sda_in = RegisterField("bb_sda_in", access_dev=WRITE_ONLY, access_bus=READ_ONLY)

	def get_registers(self):
		return [self._bb_enable, self._bb_out, self._bb_sda_in] \
			+ self.idw.get_registers()

	def get_fragment(self):
		sda_r1 = Signal()
		sda_synced = Signal()
		sync = [
			sda_r1.eq(self.sda.i),
			sda_synced.eq(sda_r1)
		]
		comb = [
			If(self._bb_enable.field.r,
				self.sda.oe.eq(self._bb_sda_oe.r),
				self.sda.o.eq(self._bb_sda_o.r),
				self.scl.eq(self._bb_scl.r)
			).Else(
				self.sda.oe.eq(1),
				self.sda.o.eq(self.idw.d),
				self.scl.eq(self.idw.clk)
			),
			self._bb_sda_in.field.w.eq(sda_synced)
		]
		return Fragment(comb, sync) + self.idw.get_fragment()

# I2C IO expander
class PCA9555Driver(BBI2CDataWriter, Actor):
	def __init__(self, cycle_bits=8, addr=0x20):
		self.addr = addr
		BBI2CDataWriter.__init__(self, cycle_bits, 32)
		Actor.__init__(self, ("program", Sink, [("addr", 8), ("data", 16)]))
	
	def get_fragment(self):
		word = Signal(32)
		addr = Signal(7)
		comb = [
			self.idw.pds.eq(self.endpoints["program"].stb),
			addr.eq(self.addr),
			word.eq(Cat(self.token("program").data, self.token("program").addr, 0, addr)),
			self.idw.pdi.eq(bitreverse(word)),
			self.busy.eq(self.idw.busy)
		]
		self.idw.fsm.act(self.idw.fsm.WAIT_DATA,
			self.endpoints["program"].ack.eq(1)
		)
		return Fragment(comb) + BBI2CDataWriter.get_fragment(self)
		
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
		
		self.clk_high = Signal()
		self.clk_low = Signal()
		
		self.eoc = Signal()
		self.ev_clk_high = Signal()
		self.ev_clk_low = Signal()
		self.ev_data = Signal()
		
		# FSM
		fsm_states = ["WAIT_DATA", "TRANSFER_DATA"] + extra_fsm_states
		self.fsm = FSM(*fsm_states)
		self.start_action = [self.fsm.next_state(self.fsm.TRANSFER_DATA)]
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
		sync += [
			If(self.clk_high,
				clk_p.eq(1)
			).Elif(self.clk_low,
				clk_p.eq(0)
			),
			self.clk.eq(clk_p)
		]
		
		# control FSM
		self.fsm.act(self.fsm.WAIT_DATA,
			cycle_counter_reset.eq(1),
			sr_load.eq(1),
			If(self.pds,
				*self.start_action
			)
		)
		self.fsm.act(self.fsm.TRANSFER_DATA,
			self.clk_high.eq(self.ev_clk_high),
			self.clk_low.eq(self.ev_clk_low),
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
		
		Actor.__init__(self, ("program", Sink, [("attn", 6)]))
	
	def get_registers(self):
		return self._sdw.get_registers() + [self._pos_le_high, self._pos_le_low]
	
	def get_fragment(self):
		comb = [
			self._sdw.pds.eq(self.endpoints["program"].stb),
			self._sdw.pdi.eq(Cat(0, self.token("program").attn))
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
		self.sdw = SerialDataWriter(cycle_bits, data_bits, ["FIRSTCLK", "CSN_HI"])
		self.sdw.start_action = [self.sdw.fsm.next_state(self.sdw.fsm.FIRSTCLK)]
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
		csn = Signal(reset=1)
		csn_p = Signal(reset=1)
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
		fsm.act(fsm.FIRSTCLK,
			self.sdw.clk_high.eq(self.sdw.ev_clk_high),
			self.sdw.clk_low.eq(self.sdw.ev_clk_low),
			If(self.sdw.eoc,
				fsm.next_state(fsm.TRANSFER_DATA)
			),
			self.spi_busy.eq(1)
		)
		fsm.act(fsm.TRANSFER_DATA,
			If(self.sdw.ev_data,
				# ENX shares the data timing
				csn_low.eq(1)
			),
			self.spi_busy.eq(1)
		)
		fsm.act(fsm.CSN_HI,
			self.sdw.clk_high.eq(self.sdw.ev_clk_high),
			self.sdw.clk_low.eq(self.sdw.ev_clk_low),
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
		Actor.__init__(self, ("program", Sink, [("channel", 1), ("gain", 6)]))
	
	def get_fragment(self):
		word = Signal(16)
		comb = [
			self.sdw.pds.eq(self.endpoints["program"].stb),
			word.eq(Cat(
				0,
				self.token("program").gain,
				1,
				self.token("program").channel)),
			self.sdw.pdi.eq(bitreverse(word)),
			self.busy.eq(self.spi_busy)
		]
		self.sdw.fsm.act(self.sdw.fsm.WAIT_DATA,
			self.endpoints["program"].ack.eq(1)
		)
		return SPIWriter.get_fragment(self) + Fragment(comb)

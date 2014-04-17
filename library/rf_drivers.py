from migen.fhdl.std import *
from migen.genlib.cdc import MultiReg
from migen.flow.actor import *
from migen.bank.description import *
from migen.genlib.fsm import FSM, NextState

class I2CDataWriter(Module, AutoCSR):
	def __init__(self, cycle_bits, data_bits):		
		# I/O signals
		self.d = Signal(reset=1)
		self.clk = Signal(reset=1)
		
		# control signals
		self.pds = Signal()
		self.pdi = Signal(data_bits)
		
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
		self.submodules.fsm = FSM()
		
		# CSRs
		self._pos_end_cycle = CSRStorage(cycle_bits, reset=300)
		self._pos_clk_high = CSRStorage(cycle_bits, reset=175)
		self._pos_data = CSRStorage(cycle_bits, reset=90)
		self._pos_start = CSRStorage(cycle_bits, reset=200)
		self._pos_stop_low = CSRStorage(cycle_bits, reset=90)
		self._pos_stop_high = CSRStorage(cycle_bits, reset=275)

		###	

		# cycle counter and events
		cycle_counter = Signal(cycle_bits)
		cycle_counter_reset = Signal()
		self.comb += self.eoc.eq(cycle_counter == self._pos_end_cycle.storage)
		self.sync += If(self.eoc | cycle_counter_reset,
				cycle_counter.eq(0)
			).Else(
				cycle_counter.eq(cycle_counter + 1)
			)
		
		self.comb += [
			self.ev_clk_high.eq(cycle_counter == self._pos_clk_high.storage),
			self.ev_clk_low.eq(cycle_counter == self._pos_end_cycle.storage),
			self.ev_data.eq(cycle_counter == self._pos_data.storage),
			self.ev_start.eq(cycle_counter == self._pos_start.storage),
			self.ev_stop_low.eq(cycle_counter == self._pos_stop_low.storage),
			self.ev_stop_high.eq(cycle_counter == self._pos_stop_high.storage)
		]
		
		# data
		sr = Signal(data_bits)
		sr_load = Signal()
		sr_shift = Signal()
		data_start = Signal()
		data_stop_low = Signal()
		data_stop_high = Signal()
		remaining_data = Signal(max=data_bits+1)
		self.sync += If(sr_load,
				sr.eq(self.pdi),
				remaining_data.eq(data_bits)
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
		
		# clock
		clk_p = Signal(reset=1)
		self.sync += [
			If(self.clk_high,
				clk_p.eq(1)
			).Elif(self.clk_low,
				clk_p.eq(0)
			),
			self.clk.eq(clk_p)
		]
		
		# control FSM
		self.fsm.act("WAIT_DATA",
			cycle_counter_reset.eq(1),
			sr_load.eq(1),
			If(self.pds, NextState("START_CONDITION"))
		)
		self.fsm.act("START_CONDITION",
			self.busy.eq(1),
			self.clk_high.eq(self.ev_clk_high),
			self.clk_low.eq(self.ev_clk_low),
			data_start.eq(self.ev_start),
			If(self.eoc, NextState("TRANSFER_DATA"))
		)
		self.fsm.act("TRANSFER_DATA",
			self.busy.eq(1),
			self.clk_high.eq(self.ev_clk_high),
			self.clk_low.eq(self.ev_clk_low),
			sr_shift.eq(self.ev_data),
			If(self.eoc & (remaining_data[0:3] == 0),
				NextState("ACK")
			)
		)
		self.fsm.act("ACK",
			self.busy.eq(1),
			self.clk_high.eq(self.ev_clk_high),
			self.clk_low.eq(self.ev_clk_low),
			If(self.eoc,
				If(remaining_data == 0,
					NextState("STOP_CONDITION")
				).Else(
					NextState("TRANSFER_DATA")
				)
			)
		)
		self.fsm.act("STOP_CONDITION",
			self.busy.eq(1),
			self.clk_high.eq(self.ev_clk_high),
			data_stop_low.eq(self.ev_stop_low),
			data_stop_high.eq(self.ev_stop_high),
			If(self.eoc, NextState("WAIT_DATA"))
		)

class BBI2CDataWriter(Module, AutoCSR):
	def __init__(self, *args, **kwargs):
		self.submodules.idw = I2CDataWriter(*args, **kwargs)

		self.sda = TSTriple(reset_o=1, reset_oe=1)
		self.scl = Signal()

		self._bb_enable = CSRStorage()
		self._bb_out = CSRStorage(3) # bb_sda_oe, bb_sda_o, bb_scl
		self._bb_sda_in = CSRStatus()

		###

		sda_synced = Signal()
		self.specials += MultiReg(self.sda.i, sda_synced)
		self.comb += [
			If(self._bb_enable.storage,
				self.sda.oe.eq(self._bb_out.storage[0]),
				self.sda.o.eq(self._bb_out.storage[1]),
				self.scl.eq(self._bb_out.storage[2])
			).Else(
				self.sda.oe.eq(1),
				self.sda.o.eq(self.idw.d),
				self.scl.eq(self.idw.clk)
			),
			self._bb_sda_in.status.eq(sda_synced)
		]

# I2C IO expander
class PCA9555Driver(BBI2CDataWriter):
	def __init__(self, pads, cycle_bits=9, addr=0x20):
		self.program = Sink([("addr", 8), ("data", 16)])
		self.busy = Signal()
		BBI2CDataWriter.__init__(self, cycle_bits, 32)
		
		###

		self.comb += pads.scl.eq(self.scl)
		self.specials += self.sda.get_tristate(pads.sda)
	
		word = Signal(32)
		saddr = Signal(7)
		self.comb += [
			self.idw.pds.eq(self.program.stb),
			saddr.eq(addr),
			word.eq(Cat(self.program.payload.data, self.program.payload.addr, 0, saddr)),
			self.idw.pdi.eq(word[::-1]),
			self.busy.eq(self.idw.busy)
		]
		self.idw.fsm.act("WAIT_DATA", self.program.ack.eq(1))
		
class SerialDataWriter(Module, AutoCSR):
	def __init__(self, cycle_bits, data_bits, def_end_cycle=20):
		# I/O signals
		self.d = Signal()
		self.clk = Signal()
		
		# control signals
		self.pds = Signal()
		self.pdi = Signal(data_bits)
		
		self.clk_high = Signal()
		self.clk_low = Signal()
		
		self.eoc = Signal()
		self.ev_clk_high = Signal()
		self.ev_clk_low = Signal()
		self.ev_data = Signal()
		
		# FSM
		self.fsm = FSM()
		self.start_action = [NextState("TRANSFER_DATA")]
		self.end_action = [NextState("WAIT_DATA")]
		
		# registers
		self._pos_end_cycle = CSRStorage(cycle_bits, reset=def_end_cycle)
		self._pos_data = CSRStorage(cycle_bits, reset=0)

		###
	
		# cycle counter and events
		cycle_counter = Signal(cycle_bits)
		self.cycle_counter_reset = Signal()
		self.comb += self.eoc.eq(cycle_counter == self._pos_end_cycle.storage)
		self.sync += If(self.eoc | self.cycle_counter_reset,
				cycle_counter.eq(0)
			).Else(
				cycle_counter.eq(cycle_counter + 1)
			)
		
		self.comb += [
			self.ev_clk_high.eq(cycle_counter == (self._pos_end_cycle.storage >> 1)),
			self.ev_clk_low.eq(cycle_counter == self._pos_end_cycle.storage),
			self.ev_data.eq(cycle_counter == self._pos_data.storage)
		]
		
		# data
		sr = Signal(data_bits)
		self.sr_load = Signal()
		self.sr_shift = Signal()
		self.remaining_data = Signal(max=data_bits+1)
		self.sync += If(self.sr_load,
				sr.eq(self.pdi),
				self.remaining_data.eq(data_bits)
			).Elif(self.sr_shift,
				sr.eq(sr[1:]),
				self.d.eq(sr[0]),
				self.remaining_data.eq(self.remaining_data-1)
			)
		
		# clock
		clk_p = Signal()
		self.sync += [
			If(self.clk_high,
				clk_p.eq(1)
			).Elif(self.clk_low,
				clk_p.eq(0)
			),
			self.clk.eq(clk_p)
		]
		
	def do_finalize(self):
		# FSM should be finalized after us
		self.submodules += self.fsm
		# control FSM
		self.fsm.act("WAIT_DATA",
			self.cycle_counter_reset.eq(1),
			self.sr_load.eq(1),
			If(self.pds,
				*self.start_action
			)
		)
		self.fsm.act("TRANSFER_DATA",
			self.clk_high.eq(self.ev_clk_high),
			self.clk_low.eq(self.ev_clk_low),
			self.sr_shift.eq(self.ev_data),
			If(self.eoc & (self.remaining_data == 0),
				*self.end_action
			)
		)

# 6-bit RF digital attenuator
class PE43602Driver(Module, AutoCSR):
	def __init__(self, pads, cycle_bits=8):
		self.submodules.sdw = SerialDataWriter(cycle_bits, 8, 12)
		self.sdw.end_action = [NextState("LE")]
		
		self._pos_le_high = CSRStorage(cycle_bits, reset=3)
		self._pos_le_low = CSRStorage(cycle_bits, reset=9)
		
		self.program = Sink([("attn", 6)])
		self.busy = Signal()
	
		###

		self.comb += [
			pads.d.eq(self.sdw.d),
			pads.clk.eq(self.sdw.clk)
		]

		self.comb += [
			self.sdw.pds.eq(self.program.stb),
			self.sdw.pdi.eq(Cat(0, self.program.payload.attn))
		]
		
		# LE counter
		le_counter = Signal(cycle_bits)
		le_counter_reset = Signal()
		self.sync += If(le_counter_reset,
				le_counter.eq(0)
			).Else(
				le_counter.eq(le_counter + 1)
			)
		
		ev_le_high = Signal()
		ev_le_low = Signal()
		self.comb += [
			ev_le_high.eq(le_counter == self._pos_le_high.storage),
			ev_le_low.eq(le_counter == self._pos_le_low.storage)
		]
		
		# LE
		le_p = Signal()
		le_high = Signal()
		le_low = Signal()
		self.sync += [
			If(le_high,
				le_p.eq(1)
			).Elif(le_low,
				le_p.eq(0)
			),
			pads.le.eq(le_p)
		]
		
		# complete FSM
		fsm = self.sdw.fsm
		fsm.act("WAIT_DATA",
			le_counter_reset.eq(1),
			self.program.ack.eq(1)
		)
		fsm.act("TRANSFER_DATA",
			le_counter_reset.eq(1),
			self.busy.eq(1)
		)
		fsm.act("LE",
			self.busy.eq(1),
			le_high.eq(ev_le_high),
			le_low.eq(ev_le_low),
			If(ev_le_low, NextState("WAIT_DATA"))
		)

class SPIWriter(Module, AutoCSR):
	def __init__(self, cycle_bits, data_bits, def_end_cycle, bidir_data):
		self.submodules.sdw = SerialDataWriter(cycle_bits, data_bits, def_end_cycle)
		self.sdw.start_action = [NextState("FIRSTCLK")]
		self.sdw.end_action = [NextState("CSN_HI")]
		
		self.csn = Signal(reset=1)
		self.clk = Signal()
		if bidir_data:
			self.data = TSTriple()
		else:
			self.mosi = Signal()
			self.miso = Signal()
		
		self.spi_busy = Signal()
		
		# bitbang control
		self._bb_enable = CSRStorage()
		self._bb_out = CSRStorage(4, reset=0x2) # bb_oe, bb_mosi, bb_csn, bb_clk
		self._bb_miso = CSRStatus()
		
		###

		# CS_N
		csn = Signal(reset=1)
		csn_p = Signal(reset=1)
		csn_high = Signal()
		csn_low = Signal()
		self.sync += [
			If(csn_high,
				csn_p.eq(1)
			).Elif(csn_low,
				csn_p.eq(0)
			),
			csn.eq(csn_p)
		]
		
		# bitbang
		if bidir_data:
			data_in_synced = Signal()
			self.specials += MultiReg(self.data.i, data_in_synced)
			self.sync += \
				If(self._bb_enable.storage,
					self.data.o.eq(self._bb_out.storage[0]),
					self.csn.eq(self._bb_out.storage[1]),
					self.clk.eq(self._bb_out.storage[2]),
					self.data.oe.eq(self._bb_out.storage[3])
				).Else(
					self.data.o.eq(self.sdw.d),
					self.csn.eq(csn),
					self.clk.eq(self.sdw.clk),
					self.data.oe.eq(1)
				)
			self.comb += self._bb_miso.status.eq(data_in_synced)
		else:
			miso_synced = Signal()
			self.specials += MultiReg(self.miso, miso_synced)
			self.comb += [
				If(self._bb_enable.storage,
					self.mosi.eq(self._bb_out.storage[0]),
					self.csn.eq(self._bb_out.storage[1]),
					self.clk.eq(self._bb_out.storage[2])
				).Else(
					self.mosi.eq(self.sdw.d),
					self.csn.eq(csn),
					self.clk.eq(self.sdw.clk)
				),
				self._bb_miso.status.eq(miso_synced)
			]
		
		# complete FSM
		fsm = self.sdw.fsm
		fsm.act("FIRSTCLK",
			self.sdw.clk_high.eq(self.sdw.ev_clk_high),
			self.sdw.clk_low.eq(self.sdw.ev_clk_low),
			If(self.sdw.eoc, NextState("TRANSFER_DATA")),
			self.spi_busy.eq(1)
		)
		fsm.act("TRANSFER_DATA",
			If(self.sdw.ev_data,
				# ENX shares the data timing
				csn_low.eq(1)
			),
			self.spi_busy.eq(1)
		)
		fsm.act("CSN_HI",
			self.sdw.clk_high.eq(self.sdw.ev_clk_high),
			self.sdw.clk_low.eq(self.sdw.ev_clk_low),
			If(self.sdw.ev_data,
				csn_high.eq(1)
			),
			If(self.sdw.eoc,
				NextState("WAIT_DATA")
			),
			self.spi_busy.eq(1)
		)
		
# RFMD's second-generation integrated synthesizer/mixer/modulator devices, e.g.
# RFMD2081 IQ Modulator with Synthesizer/VCO
# RFFC5071 Wideband Synthesizer/VCO with Integrated Mixer
class RFMDISMMDriver(SPIWriter):
	def __init__(self, pads, cycle_bits=8):
		self.program = Sink([("addr", 7), ("data", 16)])
		self.busy = Signal()
		self.locked = Signal()
		SPIWriter.__init__(self, cycle_bits, 25, 6, True)
		
		###

		self.specials += MultiReg(pads.locked, self.locked)
		self._r_locked = CSRStatus()
		self.comb += self._r_locked.status.eq(self.locked)

		self.comb += [
			pads.enx.eq(self.csn),
			pads.sclk.eq(self.clk)
		]
		self.specials += self.data.get_tristate(pads.sdata)

		word = Signal(25)
		self.comb += [
			self.sdw.pds.eq(self.program.stb),
			word.eq(Cat(self.program.payload.data, self.program.payload.addr)),
			self.sdw.pdi.eq(word[::-1]),
			self.busy.eq(self.spi_busy)
		]
		self.sdw.fsm.act("WAIT_DATA", self.program.ack.eq(1))

# Dual variable gain amplifier
class LMH6521(SPIWriter):
	def __init__(self, pads, cycle_bits=8):
		self.program = Sink([("channel", 1), ("gain", 6)])
		self.busy = Signal()
		SPIWriter.__init__(self, cycle_bits, 16, 4, False)
		
		###

		self.comb += [
			pads.scsb.eq(self.csn),
			pads.sclk.eq(self.clk),
			pads.sdi.eq(self.mosi),
			self.miso.eq(pads.sdo),
		]
	
		word = Signal(16)
		self.comb += [
			self.sdw.pds.eq(self.program.stb),
			word.eq(Cat(
				0,
				self.program.payload.gain,
				1,
				self.program.payload.channel)),
			self.sdw.pdi.eq(word[::-1]),
			self.busy.eq(self.spi_busy)
		]
		self.sdw.fsm.act("WAIT_DATA", self.program.ack.eq(1))

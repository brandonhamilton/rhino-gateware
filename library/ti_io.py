from migen.fhdl.std import *
from migen.bank.description import *
from migen.genlib.cdc import *

def _serialize4_ds(strobe, inputs, out_p, out_n):
	single_ended = Signal()
	return {
		Instance("OSERDES2",
			Instance.Parameter("DATA_WIDTH", 4),
			Instance.Parameter("DATA_RATE_OQ", "SDR"),
			Instance.Parameter("DATA_RATE_OT", "SDR"),
			Instance.Parameter("SERDES_MODE", "NONE"),
			Instance.Parameter("OUTPUT_MODE", "SINGLE_ENDED"),
			
			Instance.Input("D4", inputs[3]),
			Instance.Input("D3", inputs[2]),
			Instance.Input("D2", inputs[1]),
			Instance.Input("D1", inputs[0]),
			Instance.Output("OQ", single_ended),
			
			Instance.Input("CLK0", ClockSignal("dacio")),
			Instance.Input("CLKDIV", ClockSignal("signal")),
			Instance.Input("IOCE", strobe),
			
			Instance.Input("OCE", 1),
			Instance.Input("CLK1", 0),
			Instance.Input("RST", 0),
			Instance.Output("TQ"),
			Instance.Input("T1", 0),
			Instance.Input("T2", 0),
			Instance.Input("T3", 0),
			Instance.Input("T4", 0),
			Instance.Input("TRAIN", 0),
			Instance.Input("TCE", 1),
			Instance.Input("SHIFTIN1"),
			Instance.Input("SHIFTIN2"),
			Instance.Input("SHIFTIN3"),
			Instance.Input("SHIFTIN4"),
			Instance.Output("SHIFTOUT1"),
			Instance.Output("SHIFTOUT2"),
			Instance.Output("SHIFTOUT3"),
			Instance.Output("SHIFTOUT4")
		),
		Instance("OBUFDS",
			Instance.Input("I", single_ended),
			Instance.Output("O", out_p),
			Instance.Output("OB", out_n)
		)
	}

def _serialize8_ds(strobe, inputs, out_p, out_n):
	cascade_m2s_d = Signal()
	cascade_s2m_d = Signal()
	cascade_m2s_t = Signal()
	cascade_s2m_t = Signal()
	single_ended = Signal()
	return {
		Instance("OSERDES2",
			Instance.Parameter("DATA_WIDTH", 8),
			Instance.Parameter("DATA_RATE_OQ", "SDR"),
			Instance.Parameter("DATA_RATE_OT", "SDR"),
			Instance.Parameter("SERDES_MODE", "MASTER"),
			Instance.Parameter("OUTPUT_MODE", "SINGLE_ENDED"),
			
			Instance.Input("D4", inputs[7]),
			Instance.Input("D3", inputs[6]),
			Instance.Input("D2", inputs[5]),
			Instance.Input("D1", inputs[4]),
			Instance.Output("OQ", single_ended),
			
			Instance.Input("CLK0", ClockSignal("dacio")),
			Instance.Input("CLKDIV", ClockSignal("signal")),
			Instance.Input("IOCE", strobe),
			
			Instance.Input("OCE", 1),
			Instance.Input("CLK1", 0),
			Instance.Input("RST", 0),
			Instance.Output("TQ"),
			Instance.Input("T1", 0),
			Instance.Input("T2", 0),
			Instance.Input("T3", 0),
			Instance.Input("T4", 0),
			Instance.Input("TRAIN", 0),
			Instance.Input("TCE", 1),
			Instance.Input("SHIFTIN1", 1),
			Instance.Input("SHIFTIN2", 1),
			Instance.Input("SHIFTIN3", cascade_s2m_d),
			Instance.Input("SHIFTIN4", cascade_s2m_t),
			Instance.Output("SHIFTOUT1", cascade_m2s_d),
			Instance.Output("SHIFTOUT2", cascade_m2s_t),
			Instance.Output("SHIFTOUT3"),
			Instance.Output("SHIFTOUT4"),
			
			name="master"
		),
		Instance("OSERDES2",
			Instance.Parameter("DATA_WIDTH", 8),
			Instance.Parameter("DATA_RATE_OQ", "SDR"),
			Instance.Parameter("DATA_RATE_OT", "SDR"),
			Instance.Parameter("SERDES_MODE", "SLAVE"),
			Instance.Parameter("OUTPUT_MODE", "SINGLE_ENDED"),
		
			Instance.Input("D4", inputs[3]),
			Instance.Input("D3", inputs[2]),
			Instance.Input("D2", inputs[1]),
			Instance.Input("D1", inputs[0]),
			Instance.Output("OQ"),
			
			Instance.Input("CLK0", ClockSignal("dacio")),
			Instance.Input("CLKDIV", ClockSignal("signal")),
			Instance.Input("IOCE", strobe),
			
			Instance.Input("OCE", 1),
			Instance.Input("CLK1", 0),
			Instance.Input("RST", 0),
			Instance.Output("TQ"),
			Instance.Input("T1", 0),
			Instance.Input("T2", 0),
			Instance.Input("T3", 0),
			Instance.Input("T4", 0),
			Instance.Input("TRAIN", 0),
			Instance.Input("TCE", 1),
			Instance.Input("SHIFTIN1", cascade_m2s_d),
			Instance.Input("SHIFTIN2", cascade_m2s_t),
			Instance.Input("SHIFTIN3", 1),
			Instance.Input("SHIFTIN4", 1),
			Instance.Output("SHIFTOUT1"),
			Instance.Output("SHIFTOUT2"),
			Instance.Output("SHIFTOUT3", cascade_s2m_d),
			Instance.Output("SHIFTOUT4", cascade_s2m_t),
			
			name="slave"
		),
		Instance("OBUFDS",
			Instance.Input("I", single_ended),
			Instance.Output("O", out_p),
			Instance.Output("OB", out_n)
		)
	}

class _BaseDAC(Module, AutoCSR):
	def __init__(self, pads, serdesstrobe):
		width = 2*flen(pads.dat_p)
		
		# registers are in the system clock domain
		self._r_data_en = CSRStorage()
		self._r_test_pattern_en = CSRStorage()
		self._r_test_pattern_i0 = CSRStorage(width, reset=0x7AB6)
		self._r_test_pattern_q0 = CSRStorage(width, reset=0xEA45)
		self._r_test_pattern_i1 = CSRStorage(width, reset=0x1A16)
		self._r_test_pattern_q1 = CSRStorage(width, reset=0xAAC6)
		self._r_pulse_frame = CSR()

		# register data transferred to signal clock domain
		self._data_en = Signal()
		self._test_pattern_en = Signal()
		self._test_pattern_i0 = Signal(width)
		self._test_pattern_q0 = Signal(width)
		self._test_pattern_i1 = Signal(width)
		self._test_pattern_q1 = Signal(width)
		self._pulse_frame = Signal()				
	
		###

		ps = PulseSynchronizer("sys", "signal")
		self.submodules += ps
		self.comb += [
			ps.i.eq(self._r_pulse_frame.re),
			self._pulse_frame.eq(ps.o)
		]
		self.specials += {
			MultiReg(self._r_data_en.storage, self._data_en, "signal"),
			MultiReg(self._r_test_pattern_en.storage, self._test_pattern_en, "signal"),
			MultiReg(self._r_test_pattern_i0.storage, self._test_pattern_i0, "signal"),
			MultiReg(self._r_test_pattern_q0.storage, self._test_pattern_q0, "signal"),
			MultiReg(self._r_test_pattern_i1.storage, self._test_pattern_i1, "signal"),
			MultiReg(self._r_test_pattern_q1.storage, self._test_pattern_q1, "signal")
		}

class DAC(_BaseDAC):
	def __init__(self, pads, serdesstrobe):
		_BaseDAC.__init__(self, pads, serdesstrobe)

		# in signal clock domain
		dw = flen(pads.dat_p)
		self.i = Signal(2*dw)
		self.q = Signal(2*dw)
	
		###

		# mux test pattern, enable DAC, accept tokens
		pulse_frame_pending = Signal()
		frame_div = Signal(3)
		mi = Signal(2*dw)
		mq = Signal(2*dw)
		fr = Signal(4)
		self.comb += [
			If(self._test_pattern_en,
				If(frame_div[0],
					mi.eq(self._test_pattern_i1),
					mq.eq(self._test_pattern_q1)
				).Else(
					mi.eq(self._test_pattern_i0),
					mq.eq(self._test_pattern_q0)
				)
			).Else(
				mi.eq(self.i),
				mq.eq(self.q)
			),
			If((frame_div == 0) & (pulse_frame_pending | self._test_pattern_en | self._data_en),
				fr.eq(0xf)
			).Else(
				fr.eq(0x0)
			)
		]
		mq_d = Signal(2*dw)
		self.sync.signal += [
			If(self._pulse_frame,
				pulse_frame_pending.eq(1)
			).Elif(frame_div == 0,
				pulse_frame_pending.eq(0)
			),
			pads.txenable.eq(self._test_pattern_en | self._data_en),
			frame_div.eq(frame_div + 1),
			mq_d.eq(mq)
		]
		
		# transmit data and framing signal
		for i in range(dw):
			self.specials += _serialize4_ds(serdesstrobe,
				[mq_d[i], mi[dw+i], mi[i], mq[dw+i]],
				pads.dat_p[i], pads.dat_n[i])
		self.specials += _serialize4_ds(serdesstrobe,
			[fr[3], fr[2], fr[1], fr[0]],
			pads.frame_p, pads.frame_n)

class DAC2X(_BaseDAC):
	def __init__(self, pads, serdesstrobe):
		_BaseDAC.__init__(self, pads, serdesstrobe)

		# in signal clock domain
		dw = flen(pads.dat_p)
		self.i0 = Signal(2*dw)
		self.q0 = Signal(2*dw)
		self.i1 = Signal(2*dw)
		self.q1 = Signal(2*dw)
	
		###
		
		# mux test pattern, enable DAC, accept tokens
		pulse_frame_pending = Signal()
		frame_div = Signal(2)
		mi0 = Signal(2*dw)
		mq0 = Signal(2*dw)
		mi1 = Signal(2*dw)
		mq1 = Signal(2*dw)
		fr = Signal(8)
		self.comb += [
			If(self._test_pattern_en,
				mi0.eq(self._test_pattern_i0),
				mq0.eq(self._test_pattern_q0),
				mi1.eq(self._test_pattern_i1),
				mq1.eq(self._test_pattern_q1)
			).Else(
				mi0.eq(self.i0),
				mq0.eq(self.q0),
				mi1.eq(self.i1),
				mq1.eq(self.q1)
			),
			If((frame_div == 0) & (pulse_frame_pending | self._test_pattern_en | self._data_en),
				fr.eq(0xf0)
			).Else(
				fr.eq(0x00)
			)
		]
		mq1_d = Signal(2*dw)
		self.sync.signal += [
			If(self._pulse_frame,
				pulse_frame_pending.eq(1)
			).Elif(frame_div == 0,
				pulse_frame_pending.eq(0)
			),
			pads.txenable.eq(self._test_pattern_en | self._data_en),
			frame_div.eq(frame_div + 1),
			mq1_d.eq(mq1)
		]
		
		# transmit data and framing signal
		for i in range(dw):
			self.specials += _serialize8_ds(serdesstrobe,
				[mq1_d[i], mi0[dw+i], mi0[i], mq0[dw+i],
				 mq0[i], mi1[dw+i], mi1[i], mq1[dw+i]],
				pads.dat_p[i], pads.dat_n[i])
		self.specials += _serialize8_ds(serdesstrobe,
			[fr[7], fr[6], fr[5], fr[4],
			 fr[3], fr[2], fr[1], fr[0]],
			pads.frame_p, pads.frame_n)

class ADC(Module):
	def __init__(self, pads):
		n_io = flen(pads.dat_a_p)
		self.a = Signal(2*n_io)
		self.b = Signal(2*n_io)
	
		###

		a_noninvert = Signal(2*n_io)
		b_noninvert = Signal(2*n_io)

		for i in range(n_io):
			single_ended_a = Signal()
			single_ended_b = Signal()
			self.specials += {
				Instance("IBUFDS",
					Instance.Input("I", pads.dat_a_p[i]),
					Instance.Input("IB", pads.dat_a_n[i]),
					Instance.Output("O", single_ended_a)
				),
				Instance("IBUFDS",
					Instance.Input("I", pads.dat_b_p[i]),
					Instance.Input("IB", pads.dat_b_n[i]),
					Instance.Output("O", single_ended_b)
				),
				Instance("IDDR2",
					Instance.Parameter("DDR_ALIGNMENT", "C0"),
					Instance.Parameter("INIT_Q0", 0),
					Instance.Parameter("INIT_Q1", 0),
					Instance.Parameter("SRTYPE", "SYNC"),
					
					Instance.Input("D", single_ended_a),
					Instance.Output("Q0", a_noninvert[2*i+1]),
					Instance.Output("Q1", a_noninvert[2*i]),
					
					Instance.Input("C0", ClockSignal("signal")),
					Instance.Input("C1", ~ClockSignal("signal")),
					Instance.Input("CE", 1),
					Instance.Input("R", 0),
					Instance.Input("S", 0)
				),
				Instance("IDDR2",
					Instance.Parameter("DDR_ALIGNMENT", "C0"),
					Instance.Parameter("INIT_Q0", 0),
					Instance.Parameter("INIT_Q1", 0),
					Instance.Parameter("SRTYPE", "SYNC"),
					
					Instance.Input("D", single_ended_b),
					Instance.Output("Q0", b_noninvert[2*i+1]),
					Instance.Output("Q1", b_noninvert[2*i]),
					
					Instance.Input("C0", ClockSignal("signal")),
					Instance.Input("C1", ~ClockSignal("signal")),
					Instance.Input("CE", 1),
					Instance.Input("R", 0),
					Instance.Input("S", 0)
				)
			}

		try:
			inversions_a = pads.platform_info["inverted_pairs_a"]
		except (AttributeError, KeyError):
			inversions_a = set()
		try:
			inversions_b = pads.platform_info["inverted_pairs_b"]
		except (AttributeError, KeyError):
			inversions_b = set()
		bits_a = []
		bits_b = []
		for i in range(2*n_io):
			if i//2 in inversions_a:
				bits_a.append(~a_noninvert[i])
			else:
				bits_a.append(a_noninvert[i])
			if i//2 in inversions_b:
				bits_b.append(~b_noninvert[i])
			else:
				bits_b.append(b_noninvert[i])
		self.sync.signal += [
			self.a.eq(Cat(*bits_a)),
			self.b.eq(Cat(*bits_b))
		]

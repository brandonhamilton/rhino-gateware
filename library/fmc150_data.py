from migen.fhdl.structure import *
from migen.flow.actor import *
from migen.bank.description import *

def _serialize_ds(strobe, inputs, out_p, out_n):
	cascade_m2s_d = Signal()
	cascade_s2m_d = Signal()
	cascade_m2s_t = Signal()
	cascade_s2m_t = Signal()
	single_ended = Signal()
	return [
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
			
			Instance.ClockPort("CLK0", "io8x"),
			Instance.ClockPort("CLKDIV", "sys"),
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
			
			Instance.ClockPort("CLK0", "io8x"),
			Instance.ClockPort("CLKDIV", "sys"),
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
	]

class DAC(Actor):
	def __init__(self, pins, serdesstrobe):
		self._pins = pins
		self._serdesstrobe = serdesstrobe
		
		width = 2*len(self._pins.dat_p)
		
		self._test_pattern_en = RegisterField("test_pattern_en", 1)
		self._test_pattern_i0 = RegisterField("test_pattern_i0", width, reset=0x55aa)
		self._test_pattern_q0 = RegisterField("test_pattern_q0", width, reset=0x55aa)
		self._test_pattern_i1 = RegisterField("test_pattern_i1", width, reset=0x55aa)
		self._test_pattern_q1 = RegisterField("test_pattern_q1", width, reset=0x55aa)
		self._pulse_frame = RegisterRaw("pulse_frame", 1)
		
		super().__init__(("samples", Sink, [
			("i0", BV(width)),
			("q0", BV(width)),
			("i1", BV(width)),
			("q1", BV(width))
		]))
	
	def get_registers(self):
		return [self._test_pattern_en,
			self._test_pattern_i0, self._test_pattern_q0,
			self._test_pattern_i1, self._test_pattern_q1,
			self._pulse_frame]
	
	def get_fragment(self):
		dw = len(self._pins.dat_p)
		inst = []
		
		# mux test pattern, enable DAC, accept tokens
		token = self.token("samples")
		iotest = self._test_pattern_en.field.r
		pulse_frame = self._pulse_frame.re
		mi0 = Signal(BV(2*dw))
		mq0 = Signal(BV(2*dw))
		mi1 = Signal(BV(2*dw))
		mq1 = Signal(BV(2*dw))
		fr = Signal(BV(8))
		comb = [
			self.endpoints["samples"].ack.eq(~iotest),
			If(iotest,
				mi0.eq(token.i0),
				mq0.eq(token.q0),
				mi1.eq(token.i1),
				mq1.eq(token.q1)
			).Else(
				mi0.eq(self._test_pattern_i0.field.r),
				mq0.eq(self._test_pattern_q0.field.r),
				mi1.eq(self._test_pattern_i1.field.r),
				mq1.eq(self._test_pattern_q1.field.r)
			),
			If(iotest | self.endpoints["samples"].stb | pulse_frame,
				fr.eq(0xf0)
			).Else(
				fr.eq(0x00)
			)
		]
		sync = [
			self._pins.txenable.eq(iotest | self.endpoints["samples"].stb)
		]
		
		# transmit data and framing signal
		for i in range(dw):
			inst += _serialize_ds(self._serdesstrobe,
				[mi0[dw+i], mi0[i], mq0[dw+i], mq0[i],
				 mi1[dw+i], mi1[i], mq1[dw+i], mq1[i]],
				self._pins.dat_p[i], self._pins.dat_n[i])
		inst += _serialize_ds(self._serdesstrobe,
			[fr[7], fr[6], fr[5], fr[4],
			 fr[3], fr[2], fr[1], fr[0]],
			self._pins.frame_p, self._pins.frame_n)
		
		return Fragment(comb, sync, instances=inst)

class ADC(Actor):
	def __init__(self, pins):
		self._pins = pins
		
		width = 2*len(self._pins.dat_a_p)
		super().__init__(("samples", Source, [
			("a", BV(width)),
			("b", BV(width))
		]))
	
	def get_fragment(self):
		# push 1 token every cycle
		# We need 1 token accepted at all cycles. TODO: error reporting
		comb = [
			self.endpoints["samples"].stb.eq(1)
		]
		
		# receive data
		dw = len(self._pins.dat_a_p)
		token = self.token("samples")
		inst = []
		for i in range(dw):
			single_ended_a = Signal()
			single_ended_b = Signal()
			inst += [
				Instance("IBUFDS",
					Instance.Input("I", self._pins.dat_a_p[i]),
					Instance.Input("IB", self._pins.dat_a_n[i]),
					Instance.Output("O", single_ended_a)
				),
				Instance("IBUFDS",
					Instance.Input("I", self._pins.dat_b_p[i]),
					Instance.Input("IB", self._pins.dat_b_n[i]),
					Instance.Output("O", single_ended_b)
				),
				Instance("IDDR2",
					Instance.Parameter("DDR_ALIGNMENT", "C0"),
					Instance.Parameter("INIT_Q0", 0),
					Instance.Parameter("INIT_Q1", 0),
					Instance.Parameter("SRTYPE", "SYNC"),
					
					Instance.Input("D", single_ended_a),
					Instance.Output("Q0", token.a[2*i]),
					Instance.Output("Q1", token.a[2*i+1]),
					
					Instance.ClockPort("C0", invert=False),
					Instance.ClockPort("C1", invert=True),
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
					Instance.Output("Q0", token.b[2*i]),
					Instance.Output("Q1", token.b[2*i+1]),
					
					Instance.ClockPort("C0", invert=False),
					Instance.ClockPort("C1", invert=True),
					Instance.Input("CE", 1),
					Instance.Input("R", 0),
					Instance.Input("S", 0)
				)
			]
		
		return Fragment(comb, instances=inst)

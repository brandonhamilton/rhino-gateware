from migen.fhdl.structure import *
from migen.flow.actor import *

def _serialize_ds(strobe, inputs, out_p, out_n):
	cascade = Signal(BV(4))
	single_ended = Signal()
	return [
		Instance("OSERDES2",
			Instance.Parameter("DATA_WIDTH", 8),
			Instance.Parameter("DATA_RATE_OQ", "SDR"),
			Instance.Parameter("DATA_RATE_OT", "SDR"),
			Instance.Parameter("SERDES_MODE", "MASTER"),
			Instance.Parameter("OUTPUT_MODE","DIFFERENTIAL"),
			
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
			Instance.Input("SHIFTIN1", 0),
			Instance.Input("SHIFTIN2", 0),
			Instance.Input("SHIFTIN3", 0),
			Instance.Input("SHIFTIN4", 0),
			Instance.Output("SHIFTOUT1", cascade[0]),
			Instance.Output("SHIFTOUT2", cascade[1]),
			Instance.Output("SHIFTOUT3", cascade[2]),
			Instance.Output("SHIFTOUT4", cascade[3]),
			
			name="master"
		),
		Instance("OSERDES2",
			Instance.Parameter("DATA_WIDTH", 8),
			Instance.Parameter("DATA_RATE_OQ", "SDR"),
			Instance.Parameter("DATA_RATE_OT", "SDR"),
			Instance.Parameter("SERDES_MODE", "SLAVE"),
			Instance.Parameter("OUTPUT_MODE","DIFFERENTIAL"),
		
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
			Instance.Input("SHIFTIN1", cascade[0]),
			Instance.Input("SHIFTIN2", cascade[1]),
			Instance.Input("SHIFTIN3", cascade[2]),
			Instance.Input("SHIFTIN4", cascade[3]),
			Instance.Output("SHIFTOUT1"),
			Instance.Output("SHIFTOUT2"),
			Instance.Output("SHIFTOUT3"),
			Instance.Output("SHIFTOUT4"),
			
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
		super().__init__(("samples", Sink, [
			("i0", BV(width)),
			("q0", BV(width)),
			("i1", BV(width)),
			("q1", BV(width))
		]))
	
	def get_fragment(self):
		dw = len(self._pins.dat_p)
		inst = []
		
		# enable DAC, accept all tokens
		# We need 1 token at all cycles. TODO: error reporting
		comb = [
			self._pins.txenable.eq(1),
			self.endpoints["samples"].ack.eq(1)
		]
		
		# transmit data
		token = self.token("samples")
		for i in range(dw):
			inst += _serialize_ds(self._serdesstrobe,
				[token.i0[dw+i], token.i0[i], token.q0[dw+i], token.q0[i],
				token.i1[dw+i], token.i1[i], token.q1[dw+i], token.q1[i]],
				self._pins.dat_p[i], self._pins.dat_n[i])
		
		# transmit framing signal
		inst += _serialize_ds(self._serdesstrobe, [1, 1, 1, 1, 0, 0, 0, 0],
			self._pins.frame_p, self._pins.frame_n)
		
		return Fragment(comb, instances=inst)

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

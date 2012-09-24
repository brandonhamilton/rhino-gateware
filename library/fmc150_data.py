from migen.fhdl.structure import *
from migen.flow.actor import *

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
		
		def serialize_ds(inputs, out_p, out_n):
			cascade = Signal(BV(4))
			single_ended = Signal()
			inst += [
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
					
					Instance.ClockPort("CLK0", "sys4x"),
					Instance.ClockPort("CLKDIV", "sys"),
					Instance.Input("IOCE", self._serdesstrobe),
					
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
					
					Instance.ClockPort("CLK0", "sys4x"),
					Instance.ClockPort("CLKDIV", "sys"),
					Instance.Input("IOCE", self._serdesstrobe),
					
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
		
		# transmit data
		token = self.token("samples")
		for i in range(dw):
			serialize_ds([token.i0[dw+i], token.i0[i], token.q0[dw+i], token.q0[i]
				token.i1[dw+i], token.i1[i], token.q1[dw+i], token.q1[i]],
				self._pins.dat_p[i], self._pins.dat_n[i])
		
		# transmit framing signal
		serialize_ds([1, 1, 1, 1, 0, 0, 0, 0],
			self._pins.frame_p, self._pins.frame_n)
		
		return Fragment(comb, instances=inst)

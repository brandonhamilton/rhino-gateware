from migen.fhdl.structure import *

class CRG:
	pass

class CRG100(CRG):
	def __init__(self, baseapp):
		self.cd = ClockDomain("sys")
		self._clk = baseapp.constraints.request("clk100")
		self._rst = baseapp.constraints.request("gpio", 0)

	def get_fragment(self):
		comb = [
			self.cd.rst.eq(self._rst)
		]
		inst = Instance("IBUFGDS",
			Instance.Input("I", self._clk.p),
			Instance.Input("IB", self._clk.n),
			Instance.Output("O", self.cd.clk)
		)
		return Fragment(comb, instances=[inst])

	def get_clock_domains(self):
		return {"sys": self.cd}

# Clock generation for the FMC150
# ADC samples at 122.88MHz
#    I/O is DDR (using IDDR2)
#    => Used as 1x system clock
# DAC samples at 245.76MHz
#    I/O is DDR (using OSERDES)
#    Channels are multiplexed
#    => Generate 4x (for DAC clock pins)
#       and 8x (for OSERDES) clocks
class CRGFMC150(CRG):
	def __init__(self, baseapp):
		self.cd_sys = ClockDomain("sys")
		self.cd_sys4x = ClockDomain("sys4x")
		self.cd_io8x = ClockDomain("io8x")
		self.io8x_strb = Signal()
		
		self._fmc_clocks = baseapp.constraints.request("fmc150_clocks")
		self._rst = baseapp.constraints.request("gpio", 0)
	
	def get_fragment(self):
		# receive differential clock
		post_ibufds = Signal()
		ibufds = Instance("IBUFDS",
			Instance.Input("I", self._fmc_clocks.adc_clk_p),
			Instance.Input("IB", self._fmc_clocks.adc_clk_n),
			Instance.Output("O", post_ibufds)
		)
		
		# generate phase aligned clocks with PLL
		pll_locked = Signal()
		pll_fb = Signal()
		pll_out0 = Signal()
		pll_out1 = Signal()
		pll_out2 = Signal()
		pll = Instance("PLL_BASE",
			Instance.Parameter("BANDWIDTH", "OPTIMIZED"),
			Instance.Parameter("CLKFBOUT_MULT", 8),
			Instance.Parameter("CLKFBOUT_PHASE", 0.0),
			
			Instance.Parameter("COMPENSATION", "INTERNAL"),
			Instance.Parameter("DIVCLK_DIVIDE", 1),
			Instance.Parameter("REF_JITTER", 0.100),
			Instance.Parameter("CLK_FEEDBACK", "CLKFBOUT"),
			
			Instance.Parameter("CLKIN_PERIOD", 8.14),
			Instance.Input("CLKIN", post_ibufds),

			# 1x system clock
			Instance.Parameter("CLKOUT0_DIVIDE", 8),
			Instance.Parameter("CLKOUT0_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT0_PHASE", 0.0),
			Instance.Output("CLKOUT0", pll_out0),
			
			# 4x DAC clock
			Instance.Parameter("CLKOUT1_DIVIDE", 2),
			Instance.Parameter("CLKOUT1_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT1_PHASE", 0.0),
			Instance.Output("CLKOUT1", pll_out1),
			
			# 8x DAC SERDES clock
			Instance.Parameter("CLKOUT2_DIVIDE", 1),
			Instance.Parameter("CLKOUT2_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT2_PHASE", 0.0),
			Instance.Output("CLKOUT2", pll_out2),
			
			Instance.Parameter("CLKOUT3_DIVIDE", 8),
			Instance.Parameter("CLKOUT3_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT3_PHASE", 0.0),
			Instance.Output("CLKOUT3"),
			
			Instance.Parameter("CLKOUT4_DIVIDE", 8),
			Instance.Parameter("CLKOUT4_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT4_PHASE", 0.0),
			Instance.Output("CLKOUT4"),
			
			Instance.Parameter("CLKOUT5_DIVIDE", 8),
			Instance.Parameter("CLKOUT5_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT5_PHASE", 0.0),
			Instance.Output("CLKOUT5"),
			
			Instance.Output("LOCKED", pll_locked),
			
			Instance.Input("CLKFBIN", pll_fb),
			Instance.Output("CLKFBOUT", pll_fb),
			
			Instance.Input("RST")
		)
		
		# buffer 1x and 4x clocks
		bufg_1x = Instance("BUFG",
			Instance.Input("I", pll_out0),
			Instance.Output("O", self.cd_sys.clk)
		)
		bufg_4x = Instance("BUFG",
			Instance.Input("I", pll_out1),
			Instance.Output("O", self.cd_sys4x.clk)
		)
		
		# generate strobe and 8x I/O clock
		bufpll_8x = Instance("BUFPLL",
			Instance.Parameter("DIVIDE", 8),
			Instance.Input("PLLIN", pll_out2),
			Instance.ClockPort("GCLK"),
			Instance.Input("LOCKED", pll_locked),
			Instance.Output("IOCLK", self.cd_io8x.clk),
			Instance.Output("LOCK"),
			Instance.Output("SERDESSTROBE", self.io8x_strb)
		)
		
		# forward 4x clock to DAC
		post_oddr2 = Signal()
		oddr2_4x = Instance("ODDR2",
			Instance.Parameter("DDR_ALIGNMENT", "NONE"),
			Instance.Output("Q", post_oddr2),
			Instance.Input("C0"),
			Instance.Input("C1"),
			Instance.Input("CE"),
			Instance.Input("D0"),
			Instance.Input("D1"),
			Instance.Input("R"),
			Instance.Input("S")
		)
		obufds_4x = Instance("OBUFDS",
			Instance.Input("I", post_oddr2),
			Instance.Output("O", self._fmc_clocks.dac_clk_p),
			Instance.Output("OB", self._fmc_clocks.dac_clk_n)
		)
		
		# TODO: support expressions in instance ports
		# TODO: support clock polarity in instance clock ports
		comb = [
			self.cd_sys.rst.eq(self._rst),
			
			oddr2_4x.get_io("C0").eq(self.cd_sys4x.clk),
			oddr2_4x.get_io("C1").eq(~self.cd_sys4x.clk),
			oddr2_4x.get_io("CE").eq(1),
			oddr2_4x.get_io("D0").eq(1),
			oddr2_4x.get_io("D1").eq(0),
			oddr2_4x.get_io("R").eq(0),
			oddr2_4x.get_io("S").eq(0)
		]
		
		return Fragment(comb, instances=[ibufds, pll,
			bufg_1x, bufg_4x, bufpll_8x,
			oddr2_4x, obufds_4x])
	
	def get_clock_domains(self):
		return {
			"sys":   self.cd_sys,
			"sys4x": self.cd_sys4x,
			"io8x":  self.cd_io8x
		}

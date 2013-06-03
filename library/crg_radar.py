from fractions import Fraction

from migen.fhdl.std import *
from migen.bank.description import *

# Clock generator for radar-type applications using TI ADC/DAC
#
# Free-running differential input clock is fed into a DCM that
# generates a 120MHz system clock.
#
# ADC samples at F MHz
#    I/O is DDR (using IDDR2)
#    => Used as 1x signal clock
#
# When double_dac=False:
#   DAC samples at F MHz
#      I/O is DDR (using OSERDES)
#      Channels are multiplexed
#      => Generate 2x (for DAC clock pins)
#         and 4x (for OSERDES) clocks
#
# When double_dac=True:
#   DAC samples at 2F MHz
#      I/O is DDR (using OSERDES)
#      Channels are multiplexed
#      => Generate 4x (for DAC clock pins)
#         and 8x (for OSERDES) clocks
class CRGRadar(Module, AutoCSR):
	def __init__(self, platform, free_run_clk, free_run_period, signal_clks, adc_period, double_dac):
		self.clock_domains.cd_sys = ClockDomain()
		self.clock_domains.cd_signal = ClockDomain()
		self.clock_domains.cd_dac = ClockDomain()
		self.clock_domains.cd_dacio = ClockDomain()
		self.dacio_strb = Signal()
		
		free_run_isdiff = hasattr(free_run_clk, "p")
		free_run_cstsig = free_run_clk.p if free_run_isdiff else free_run_clk

		platform.add_platform_command("""
NET "{clk_freerun}" TNM_NET = "GRPclk_freerun";
NET "{clk_adc}" TNM_NET = "GRPclk_adc";
TIMESPEC "TSclk_freerun" = PERIOD "GRPclk_freerun" """+str(float(free_run_period))+""" ns HIGH 50%;
TIMESPEC "TSclk_adc" = PERIOD "GRPclk_adc" """+str(float(adc_period))+""" ns HIGH 50%;
""", clk_freerun=free_run_cstsig, clk_adc=signal_clks.adc_clk_p)
		
		self._r_pll_enable = CSRStorage()
		self._r_pll_locked = CSRStatus()
	
		# buffer free-running clock and generate 120MHz system clock
		freerun_buffered = Signal()
		if free_run_isdiff:
			self.specials += Instance("IBUFDS",
				Instance.Input("I", free_run_clk.p),
				Instance.Input("IB", free_run_clk.n),
				Instance.Output("O", freerun_buffered)
			)
		else:
			self.specials += Instance("IBUF",
				Instance.Input("I", free_run_clk),
				Instance.Output("O", freerun_buffered)
			)
		sys_period = Fraction(1000, 120)
		sys_ratio = Fraction(free_run_period/sys_period)
		sys_clk_unbuffered = Signal()
		self.specials += Instance("DCM_CLKGEN",
			Instance.Parameter("CLKFX_DIVIDE", sys_ratio.denominator),
			Instance.Parameter("CLKFX_MD_MAX", float(sys_ratio)),
			Instance.Parameter("CLKFX_MULTIPLY", sys_ratio.numerator),
			Instance.Parameter("CLKIN_PERIOD", float(free_run_period)),
			Instance.Parameter("SPREAD_SPECTRUM", "NONE"),
			Instance.Parameter("STARTUP_WAIT", "TRUE"),
			Instance.Output("CLKFX", sys_clk_unbuffered),
			Instance.Input("CLKIN", freerun_buffered),
			Instance.Input("FREEZEDCM", 0),
			Instance.Input("PROGCLK", 0),
			Instance.Input("PROGEN", 0),
			Instance.Input("RST", 0)
		)
		self.specials += Instance("BUFG",
			Instance.Input("I", sys_clk_unbuffered),
			Instance.Output("O", self.cd_sys.clk)
		)
		
		# receive differential ADC clock and generate phase aligned clocks
		adc_buffered = Signal()
		self.specials += Instance("IBUFGDS",
			Instance.Input("I", signal_clks.adc_clk_p),
			Instance.Input("IB", signal_clks.adc_clk_n),
			Instance.Output("O", adc_buffered)
		)
		pll_reset = Signal()
		pll_locked = Signal()
		pll_fb1 = Signal()
		pll_fb2 = Signal()
		pll_out0 = Signal()
		pll_out1 = Signal()
		pll_out2 = Signal()
		self.specials += Instance("PLL_BASE",
			Instance.Parameter("BANDWIDTH", "OPTIMIZED"),
			Instance.Parameter("CLKFBOUT_MULT", 8),
			Instance.Parameter("CLKFBOUT_PHASE", 180.0),
			
			Instance.Parameter("COMPENSATION", "SOURCE_SYNCHRONOUS"),
			Instance.Parameter("DIVCLK_DIVIDE", 1),
			Instance.Parameter("REF_JITTER", 0.100),
			Instance.Parameter("CLK_FEEDBACK", "CLKFBOUT"),
			
			Instance.Parameter("CLKIN_PERIOD", float(adc_period)),
			Instance.Input("CLKIN", adc_buffered),

			# 1x signal clock
			Instance.Parameter("CLKOUT0_DIVIDE", 8),
			Instance.Parameter("CLKOUT0_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT0_PHASE", 0.0),
			Instance.Output("CLKOUT0", pll_out0),
			
			# 4x (8x) DAC SERDES clock
			Instance.Parameter("CLKOUT1_DIVIDE", 1 if double_dac else 2),
			Instance.Parameter("CLKOUT1_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT1_PHASE", 0.0),
			Instance.Output("CLKOUT1", pll_out1),
			
			# 2x (4x) DAC clock
			Instance.Parameter("CLKOUT2_DIVIDE", 2 if double_dac else 4),
			Instance.Parameter("CLKOUT2_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT2_PHASE", -45.0),
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
			
			Instance.Input("CLKFBIN", pll_fb1),
			Instance.Output("CLKFBOUT", pll_fb2),
			
			Instance.Input("RST", pll_reset)
		)
		self.specials += Instance("BUFG",
			Instance.Input("I", pll_fb2),
			Instance.Output("O", pll_fb1)
		)
		self.specials += Instance("BUFG",
			Instance.Input("I", pll_out0),
			Instance.Output("O", self.cd_signal.clk)
		)
		self.specials += Instance("BUFG",
			Instance.Input("I", pll_out2),
			Instance.Output("O", self.cd_dac.clk)
		)
		
		# generate strobe and DAC I/O clock
		self.specials += Instance("BUFPLL",
			Instance.Parameter("DIVIDE", 8 if double_dac else 4),
			Instance.Input("PLLIN", pll_out1),
			Instance.Input("GCLK", ClockSignal("signal")),
			Instance.Input("LOCKED", pll_locked),
			Instance.Output("IOCLK", self.cd_dacio.clk),
			Instance.Output("LOCK"),
			Instance.Output("SERDESSTROBE", self.dacio_strb)
		)
		
		# forward clock to DAC
		dac_clk_se = Signal()
		self.specials += Instance("ODDR2",
			Instance.Parameter("DDR_ALIGNMENT", "NONE"),
			Instance.Output("Q", dac_clk_se),
			Instance.Input("C0", ClockSignal("dac")),
			Instance.Input("C1", ~ClockSignal("dac")),
			Instance.Input("CE", 1),
			Instance.Input("D0", 1),
			Instance.Input("D1", 0),
			Instance.Input("R", 0),
			Instance.Input("S", 0)
		)
		self.specials += Instance("OBUFDS",
			Instance.Input("I", dac_clk_se),
			Instance.Output("O", signal_clks.dac_clk_p),
			Instance.Output("OB", signal_clks.dac_clk_n)
		)
		
		self.specials += Instance("SRL16E",
			Instance.Parameter("INIT", 0xffff),
			Instance.Input("CLK", ClockSignal()),
			Instance.Input("CE", 1),
			Instance.Input("D", 0),
			Instance.Input("A0", 1),
			Instance.Input("A1", 1),
			Instance.Input("A2", 1),
			Instance.Input("A3", 1),
			Instance.Output("Q", self.cd_sys.rst)
		)
		
		self.comb += [
			pll_reset.eq(~self._r_pll_enable.storage),
			self._r_pll_locked.status.eq(pll_locked)
		]

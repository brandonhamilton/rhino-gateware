from fractions import Fraction

from migen.fhdl.structure import *
from migen.bank.description import *
from mibuild.crg import CRG

from library.uid import UID_CRG_RADAR

class CRG100(CRG):
	def __init__(self, baseapp):
		self.cd = ClockDomain("sys")
		self._clk = baseapp.mplat.request("clk100")
		
		baseapp.mplat.add_platform_command("""
NET "{clk_100}" TNM_NET = "GRPclk_100";
TIMESPEC "TSclk_100" = PERIOD "GRPclk_100" 10 ns HIGH 50%;
""", clk_100=self._clk.p)

	def get_fragment(self):
		ibufg = Instance("IBUFGDS",
			Instance.Input("I", self._clk.p),
			Instance.Input("IB", self._clk.n),
			Instance.Output("O", self.cd.clk)
		)
		srl_reset = Instance("SRL16E",
			Instance.Parameter("INIT", 0xffff),
			Instance.ClockPort("CLK"),
			Instance.Input("CE", 1),
			Instance.Input("D", 0),
			Instance.Input("A0", 1),
			Instance.Input("A1", 1),
			Instance.Input("A2", 1),
			Instance.Input("A3", 1),
			Instance.Output("Q", self.cd.rst)
		)
		return Fragment(instances={ibufg, srl_reset})

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
class CRGRadar(CRG):
	def __init__(self, baseapp, free_run_clk, free_run_period, signal_clks, adc_period,
	  csr_name="crg", double_dac=True):
		self._free_run_clk = free_run_clk
		self._free_run_period = free_run_period
		self._signal_clks = signal_clks
		self._adc_period = adc_period
		self._double_dac = double_dac
		
		self.cd_sys = ClockDomain("sys")
		self.cd_signal = ClockDomain("signal")
		self.cd_dac = ClockDomain("dac")
		self.cd_dacio = ClockDomain("dacio")
		self.dacio_strb = Signal()
		
		baseapp.mplat.add_platform_command("""
NET "{clk_freerun}" TNM_NET = "GRPclk_freerun";
NET "{clk_adc}" TNM_NET = "GRPclk_adc";
TIMESPEC "TSclk_freerun" = PERIOD "GRPclk_freerun" """+str(float(self._free_run_period))+""" ns HIGH 50%;
TIMESPEC "TSclk_adc" = PERIOD "GRPclk_adc" """+str(float(self._adc_period))+""" ns HIGH 50%;
""", clk_freerun=self._free_run_clk.p, clk_adc=self._signal_clks.adc_clk_p)
		
		self.reg_pll_enable = RegisterField("pll_enable")
		self.reg_pll_locked = RegisterField("pll_locked", access_bus=READ_ONLY, access_dev=WRITE_ONLY)
		baseapp.csrs.request(csr_name, UID_CRG_RADAR, self.reg_pll_enable, self.reg_pll_locked)
	
	def get_fragment(self):
		# receive differential free-running clock and generate 120MHz system clock
		freerun_buffered = Signal()
		freerun_buffer = Instance("IBUFDS",
			Instance.Input("I", self._free_run_clk.p),
			Instance.Input("IB", self._free_run_clk.n),
			Instance.Output("O", freerun_buffered)
		)
		sys_period = Fraction(1000, 120)
		sys_ratio = Fraction(self._free_run_period/sys_period)
		sys_clk_unbuffered = Signal()
		dcm_sys = Instance("DCM_CLKGEN",
			Instance.Parameter("CLKFX_DIVIDE", sys_ratio.denominator),
			Instance.Parameter("CLKFX_MD_MAX", float(sys_ratio)),
			Instance.Parameter("CLKFX_MULTIPLY", sys_ratio.numerator),
			Instance.Parameter("CLKIN_PERIOD", float(self._free_run_period)),
			Instance.Parameter("SPREAD_SPECTRUM", "NONE"),
			Instance.Parameter("STARTUP_WAIT", "TRUE"),
			Instance.Output("CLKFX", sys_clk_unbuffered),
			Instance.Input("CLKIN", freerun_buffered),
			Instance.Input("FREEZEDCM", 0),
			Instance.Input("PROGCLK", 0),
			Instance.Input("PROGEN", 0),
			Instance.Input("RST", 0)
		)
		bufg_sys = Instance("BUFG",
			Instance.Input("I", sys_clk_unbuffered),
			Instance.Output("O", self.cd_sys.clk)
		)
		
		# receive differential ADC clock and generate phase aligned clocks
		adc_buffered = Signal()
		adc_buffer = Instance("IBUFGDS",
			Instance.Input("I", self._signal_clks.adc_clk_p),
			Instance.Input("IB", self._signal_clks.adc_clk_n),
			Instance.Output("O", adc_buffered)
		)
		pll_reset = Signal()
		pll_locked = Signal()
		pll_fb1 = Signal()
		pll_fb2 = Signal()
		pll_out0 = Signal()
		pll_out1 = Signal()
		pll_out2 = Signal()
		pll = Instance("PLL_BASE",
			Instance.Parameter("BANDWIDTH", "OPTIMIZED"),
			Instance.Parameter("CLKFBOUT_MULT", 8),
			Instance.Parameter("CLKFBOUT_PHASE", -90.0),
			
			Instance.Parameter("COMPENSATION", "SOURCE_SYNCHRONOUS"),
			Instance.Parameter("DIVCLK_DIVIDE", 1),
			Instance.Parameter("REF_JITTER", 0.100),
			Instance.Parameter("CLK_FEEDBACK", "CLKFBOUT"),
			
			Instance.Parameter("CLKIN_PERIOD", float(self._adc_period)),
			Instance.Input("CLKIN", adc_buffered),

			# 1x signal clock
			Instance.Parameter("CLKOUT0_DIVIDE", 8),
			Instance.Parameter("CLKOUT0_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT0_PHASE", 0.0),
			Instance.Output("CLKOUT0", pll_out0),
			
			# 4x (8x) DAC SERDES clock
			Instance.Parameter("CLKOUT1_DIVIDE", 1 if self._double_dac else 2),
			Instance.Parameter("CLKOUT1_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT1_PHASE", 0.0),
			Instance.Output("CLKOUT1", pll_out1),
			
			# 2x (4x) DAC clock
			Instance.Parameter("CLKOUT2_DIVIDE", 2 if self._double_dac else 4),
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
		bufg_fb = Instance("BUFG",
			Instance.Input("I", pll_fb2),
			Instance.Output("O", pll_fb1)
		)
		bufg_signal = Instance("BUFG",
			Instance.Input("I", pll_out0),
			Instance.Output("O", self.cd_signal.clk)
		)
		bufg_dac = Instance("BUFG",
			Instance.Input("I", pll_out2),
			Instance.Output("O", self.cd_dac.clk)
		)
		
		# generate strobe and DAC I/O clock
		bufpll_dacio = Instance("BUFPLL",
			Instance.Parameter("DIVIDE", 8 if self._double_dac else 4),
			Instance.Input("PLLIN", pll_out1),
			Instance.ClockPort("GCLK", "signal"),
			Instance.Input("LOCKED", pll_locked),
			Instance.Output("IOCLK", self.cd_dacio.clk),
			Instance.Output("LOCK"),
			Instance.Output("SERDESSTROBE", self.dacio_strb)
		)
		
		# forward clock to DAC
		dac_clk_se = Signal()
		oddr2_dac = Instance("ODDR2",
			Instance.Parameter("DDR_ALIGNMENT", "NONE"),
			Instance.Output("Q", dac_clk_se),
			Instance.ClockPort("C0", "dac", invert=False),
			Instance.ClockPort("C1", "dac", invert=True),
			Instance.Input("CE", 1),
			Instance.Input("D0", 1),
			Instance.Input("D1", 0),
			Instance.Input("R", 0),
			Instance.Input("S", 0)
		)
		obufds_dac = Instance("OBUFDS",
			Instance.Input("I", dac_clk_se),
			Instance.Output("O", self._signal_clks.dac_clk_p),
			Instance.Output("OB", self._signal_clks.dac_clk_n)
		)
		
		srl_reset = Instance("SRL16E",
			Instance.Parameter("INIT", 0xffff),
			Instance.ClockPort("CLK"),
			Instance.Input("CE", 1),
			Instance.Input("D", 0),
			Instance.Input("A0", 1),
			Instance.Input("A1", 1),
			Instance.Input("A2", 1),
			Instance.Input("A3", 1),
			Instance.Output("Q", self.cd_sys.rst)
		)
		
		comb = [
			pll_reset.eq(~self.reg_pll_enable.field.r),
			self.reg_pll_locked.field.w.eq(pll_locked)
		]
		
		return Fragment(comb, instances={freerun_buffer,
			dcm_sys, bufg_sys, adc_buffer, pll, bufg_fb,
			bufg_signal, bufg_dac, bufpll_dacio, oddr2_dac,
			obufds_dac, srl_reset})


# Clock generation for the FMC150
#
# Free running clock from RHINO is 100MHz.
#
# ADC samples at 122.88MHz
# When double_dac=False:
#   DAC samples at 122.88MHz
#      => Generate 2x (245.76MHz for DAC clock pins)
#         and 4x (491.52MHz for OSERDES) clocks
# When double_dac=True:
#   DAC samples at 245.76MHz
#      => Generate 4x (491.52MHz for DAC clock pins)
#         and 8x (983.04MHz for OSERDES) clocks
class CRGFMC150(CRGRadar):
	def __init__(self, baseapp, csr_name="crg", double_dac=True):
		clk100 = baseapp.mplat.request("clk100")
		fmc_clocks = baseapp.mplat.request("fmc150_clocks")
		CRGRadar.__init__(self, baseapp, clk100, 10, fmc_clocks, 8.13, csr_name, double_dac)

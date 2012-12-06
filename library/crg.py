from migen.fhdl.structure import *
from migen.bank.description import *

from library.uid import UID_FMC150_CRG

class CRG:
	pass

class CRG100(CRG):
	def __init__(self, baseapp):
		self.cd = ClockDomain("sys")
		self._clk = baseapp.constraints.request("clk100")
		
		baseapp.constraints.add_platform_command("""
NET "{clk_100}" TNM_NET = "GRPclk_100";
TIMESPEC "TSclk_100" = PERIOD "GRPclk_100" 10 ns HIGH 50%;
""", clk_100=self._clk.p)

	def get_fragment(self):
		ibufg = Instance("IBUFGDS",
			Instance.Input("I", self._clk.p),
			Instance.Input("IB", self._clk.n),
			Instance.Output("O", self.cd.clk)
		)
		reset_srl = Instance("SRL16E",
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
		return Fragment(instances=[ibufg, reset_srl])

	def get_clock_domains(self):
		return {"sys": self.cd}

# Clock generation for the FMC150
# ADC samples at 122.88MHz
#    I/O is DDR (using IDDR2)
#    => Used as 1x system clock
#
# When double_dac=False:
#   DAC samples at 122.88MHz
#      I/O is DDR (using OSERDES)
#      Channels are multiplexed
#      => Generate 2x (245.76MHz for DAC clock pins)
#         and 4x (491.52MHz for OSERDES) clocks
#
# When double_dac=True:
#   DAC samples at 245.76MHz
#      I/O is DDR (using OSERDES)
#      Channels are multiplexed
#      => Generate 4x (491.52MHz for DAC clock pins)
#         and 8x (983.04MHz for OSERDES) clocks
class CRGFMC150(CRG):
	def __init__(self, baseapp, csr_name="crg", double_dac=True):
		self._double_dac = double_dac
		
		self.cd_sys = ClockDomain("sys")
		self.cd_dac = ClockDomain("dac")
		self.cd_dacio = ClockDomain("dacio")
		self.dacio_strb = Signal()
		
		self._clk100 = baseapp.constraints.request("clk100")
		self._fmc_clocks = baseapp.constraints.request("fmc150_clocks")

		baseapp.constraints.add_platform_command("""
NET "{clk_100}" TNM_NET = "GRPclk_100";
NET "{clk_adc}" TNM_NET = "GRPclk_adc";
TIMESPEC "TSclk_100" = PERIOD "GRPclk_100" 10 ns HIGH 50%;
TIMESPEC "TSclk_adc" = PERIOD "GRPclk_adc" 8.13 ns HIGH 50%;
""", clk_100=self._clk100.p, clk_adc=self._fmc_clocks.adc_clk_p)
		
		self.reg_pll_enable = RegisterField("pll_enable")
		self.reg_pll_locked = RegisterField("pll_locked", access_bus=READ_ONLY, access_dev=WRITE_ONLY)
		self.reg_clock_sel = RegisterField("clock_sel")
		baseapp.csrs.request(csr_name, UID_FMC150_CRG, self.reg_pll_enable, self.reg_pll_locked, self.reg_clock_sel)
	
	def get_fragment(self):
		# receive differential 100MHz clock
		post_ibufds100 = Signal()
		ibufds100 = Instance("IBUFDS",
			Instance.Input("I", self._clk100.p),
			Instance.Input("IB", self._clk100.n),
			Instance.Output("O", post_ibufds100)
		)
		
		# receive differential ADC clock
		post_ibufgds = Signal()
		ibufgds = Instance("IBUFGDS",
			Instance.Input("I", self._fmc_clocks.adc_clk_p),
			Instance.Input("IB", self._fmc_clocks.adc_clk_n),
			Instance.Output("O", post_ibufgds)
		)
		
		# generate phase aligned clocks with PLL
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
			
			Instance.Parameter("CLKIN_PERIOD", 8.13),
			Instance.Input("CLKIN", post_ibufgds),

			# 1x system clock
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
		
		# buffer 1x and DAC clocks
		# 1x clock can be replaced with 100MHz clock, used during system configuration
		pll_out0G = Signal()
		bufg_pll0 = Instance("BUFG",
			Instance.Input("I", pll_out0),
			Instance.Output("O", pll_out0G)
		)
		bufg_1x = Instance("BUFGMUX",
			Instance.Input("S", self.reg_clock_sel.field.r),
			Instance.Input("I0", post_ibufds100),
			Instance.Input("I1", pll_out0G),
			Instance.Output("O", self.cd_sys.clk)
		)
		bufg_dac = Instance("BUFG",
			Instance.Input("I", pll_out2),
			Instance.Output("O", self.cd_dac.clk)
		)
		
		# generate strobe and DAC I/O clock
		bufpll_dacio = Instance("BUFPLL",
			Instance.Parameter("DIVIDE", 8 if self._double_dac else 4),
			Instance.Input("PLLIN", pll_out1),
			Instance.Input("GCLK", pll_out0G),
			Instance.Input("LOCKED", pll_locked),
			Instance.Output("IOCLK", self.cd_dacio.clk),
			Instance.Output("LOCK"),
			Instance.Output("SERDESSTROBE", self.dacio_strb)
		)
		
		# forward clock to DAC
		post_oddr2 = Signal()
		oddr2_dac = Instance("ODDR2",
			Instance.Parameter("DDR_ALIGNMENT", "NONE"),
			Instance.Output("Q", post_oddr2),
			Instance.ClockPort("C0", "dac", invert=False),
			Instance.ClockPort("C1", "dac", invert=True),
			Instance.Input("CE", 1),
			Instance.Input("D0", 1),
			Instance.Input("D1", 0),
			Instance.Input("R", 0),
			Instance.Input("S", 0)
		)
		obufds_dac = Instance("OBUFDS",
			Instance.Input("I", post_oddr2),
			Instance.Output("O", self._fmc_clocks.dac_clk_p),
			Instance.Output("OB", self._fmc_clocks.dac_clk_n)
		)
		
		reset_srl = Instance("SRL16E",
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
		
		return Fragment(comb, instances=[ibufds100, ibufgds,
			pll, bufg_fb, bufg_pll0,
			bufg_1x, bufg_dac, bufpll_dacio,
			oddr2_dac, obufds_dac,
			reset_srl])
	
	def get_clock_domains(self):
		return {
			"sys":   self.cd_sys,
			"dac":   self.cd_dac,
			"dacio": self.cd_dacio
		}

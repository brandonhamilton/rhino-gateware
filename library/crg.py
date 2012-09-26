from migen.fhdl.structure import *
from migen.bank.description import *

from library.uid import UID_FMC150_CRG

class CRG:
	pass

class CRG100(CRG):
	def __init__(self, baseapp):
		self.cd = ClockDomain("sys")
		self._clk = baseapp.constraints.request("clk100")
		self._rst = baseapp.constraints.request("gpio", 0)
		
		baseapp.constraints.add_platform_command("""
NET "{clk_100}" TNM_NET = "GRPclk_100";
TIMESPEC "TSclk_100" = PERIOD "GRPclk_100" 10 ns HIGH 50%;
""", clk_100=self._clk.p)

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
#    => Generate 4x (491.52MHz for DAC clock pins)
#       and 8x (983.04MHz for OSERDES) clocks
class CRGFMC150(CRG):
	def __init__(self, baseapp, csr_name="crg"):
		self.cd_sys = ClockDomain("sys")
		self.cd_sys4x = ClockDomain("sys4x")
		self.cd_io8x = ClockDomain("io8x")
		self.io8x_strb = Signal()
		
		self._clk100 = baseapp.constraints.request("clk100")
		self._fmc_clocks = baseapp.constraints.request("fmc150_clocks")
		self._rst = baseapp.constraints.request("gpio", 0)
		
		baseapp.constraints.add_platform_command("""
NET "{clk_100}" TNM_NET = "GRPclk_100";
NET "{clk_adc}" TNM_NET = "GRPclk_adc";
TIMESPEC "TSclk_100" = PERIOD "GRPclk_100" 10 ns HIGH 50%;
TIMESPEC "TSclk_adc" = PERIOD "GRPclk_adc" 8.13 ns HIGH 50%;
""", clk_100=self._clk100.p, clk_adc=self._fmc_clocks.adc_clk_p)
		
		self.reg_pll_enable = RegisterField("pll_enable", 1)
		self.reg_pll_locked = RegisterField("pll_locked", 1, access_bus=READ_ONLY, access_dev=WRITE_ONLY)
		self.reg_clock_sel = RegisterField("clock_sel", 1)
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
		post_ibufds = Signal()
		ibufds = Instance("IBUFDS",
			Instance.Input("I", self._fmc_clocks.adc_clk_p),
			Instance.Input("IB", self._fmc_clocks.adc_clk_n),
			Instance.Output("O", post_ibufds)
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
			Instance.Parameter("CLKFBOUT_PHASE", 0.0),
			
			Instance.Parameter("COMPENSATION", "SYSTEM_SYNCHRONOUS"),
			Instance.Parameter("DIVCLK_DIVIDE", 1),
			Instance.Parameter("REF_JITTER", 0.100),
			Instance.Parameter("CLK_FEEDBACK", "CLKFBOUT"),
			
			Instance.Parameter("CLKIN_PERIOD", 8.13),
			Instance.Input("CLKIN", post_ibufds),

			# 1x system clock
			Instance.Parameter("CLKOUT0_DIVIDE", 8),
			Instance.Parameter("CLKOUT0_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT0_PHASE", 0.0),
			Instance.Output("CLKOUT0", pll_out0),
			
			# 8x DAC SERDES clock
			Instance.Parameter("CLKOUT1_DIVIDE", 1),
			Instance.Parameter("CLKOUT1_DUTY_CYCLE", 0.5),
			Instance.Parameter("CLKOUT1_PHASE", 0.0),
			Instance.Output("CLKOUT1", pll_out1),
			
			# 4x DAC clock
			Instance.Parameter("CLKOUT2_DIVIDE", 2),
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
			
			Instance.Input("CLKFBIN", pll_fb1),
			Instance.Output("CLKFBOUT", pll_fb2),
			
			Instance.Input("RST", pll_reset)
		)
		bufg_fb = Instance("BUFG",
			Instance.Input("I", pll_fb2),
			Instance.Output("O", pll_fb1)
		)
		
		# buffer 1x and 4x clocks
		# 1x clock can be replaced with 100MHz clock, used during system configuration
		bufg_1x = Instance("BUFGMUX",
			Instance.Input("S", self.reg_clock_sel.field.r),
			Instance.Input("I0", post_ibufds100),
			Instance.Input("I1", pll_out0),
			Instance.Output("O", self.cd_sys.clk)
		)
		bufg_4x = Instance("BUFG",
			Instance.Input("I", pll_out2),
			Instance.Output("O", self.cd_sys4x.clk)
		)
		
		# generate strobe and 8x I/O clock
		bufpll_8x = Instance("BUFPLL",
			Instance.Parameter("DIVIDE", 8),
			Instance.Input("PLLIN", pll_out1),
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
			Instance.ClockPort("C0", "sys4x", invert=False),
			Instance.ClockPort("C1", "sys4x", invert=True),
			Instance.Input("CE", 1),
			Instance.Input("D0", 1),
			Instance.Input("D1", 0),
			Instance.Input("R", 0),
			Instance.Input("S", 0)
		)
		obufds_4x = Instance("OBUFDS",
			Instance.Input("I", post_oddr2),
			Instance.Output("O", self._fmc_clocks.dac_clk_p),
			Instance.Output("OB", self._fmc_clocks.dac_clk_n)
		)
		
		comb = [
			self.cd_sys.rst.eq(self._rst),
			pll_reset.eq(~self.reg_pll_enable.field.r),
			self.reg_pll_locked.field.w.eq(pll_locked)
		]
		
		return Fragment(comb, instances=[ibufds100, ibufds,
			pll, bufg_fb,
			bufg_1x, bufg_4x, bufpll_8x,
			oddr2_4x, obufds_4x])
	
	def get_clock_domains(self):
		return {
			"sys":   self.cd_sys,
			"sys4x": self.cd_sys4x,
			"io8x":  self.cd_io8x
		}

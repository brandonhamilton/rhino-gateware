from migen.fhdl.structure import *
from migen.fhdl.module import Module
from migen.fhdl.specials import Instance

from library.crg_radar import CRGRadar

class CRGDiffBasic(Module):
	def __init__(self, platform, pads, period=10.0):
		self.clock_domains.cd_sys = ClockDomain()
		platform.add_platform_command("""
NET "{clk}" TNM_NET = "GRPclk";
TIMESPEC "TSclk" = PERIOD "GRPclk" """+str(float(period))+""" ns HIGH 50%;
""", clk=pads.p)
		self.specials += Instance("IBUFGDS",
			Instance.Input("I", pads.p),
			Instance.Input("IB", pads.n),
			Instance.Output("O", self.cd_sys.clk)
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
			Instance.Output("Q", self.cd_sys.rst))

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
	def __init__(self, platform, clk100_pads, fmc_clock_pads, double_dac):
		CRGRadar.__init__(self, platform, clk100_pads, 10, fmc_clock_pads, 8.13, double_dac)

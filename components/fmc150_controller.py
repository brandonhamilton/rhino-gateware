from migen.fhdl.structure import *
from migen.fhdl.module import Module
from migen.genlib.cdc import MultiReg
from migen.bank.description import *

class FMC150Controller(Module, AutoCSR):
	def __init__(self, pads):
		for name, is_output in [
			("spi_sclk", True),
			("spi_data", True),
			
			("adc_sdo", False),
			("adc_en_n", True),
			("adc_reset", True),
			
			("cdce_sdo", False),
			("cdce_en_n", True),
			("cdce_reset_n", True),
			("cdce_pd_n", True),
			("cdce_pll_status", False),
			("cdce_ref_en", True),
			
			("dac_sdo", False),
			("dac_en_n", True),
			
			("mon_sdo", False),
			("mon_en_n", True),
			("mon_reset_n", True)
		]:
			if is_output:
				reset = 1 if name in ["adc_en_n", "cdce_en_n", "dac_en_n", "mon_en_n"] else 0
				csr = CSRStorage(name=name, reset=reset)
				self.comb += getattr(pads, name).eq(csr.storage)
			else:
				csr = CSRStatus(name=name)
				self.specials += MultiReg(getattr(pads, name), csr.status)
			setattr(self, "_r_"+name, csr)

		self.comb += pads.pg_c2m.eq(1)

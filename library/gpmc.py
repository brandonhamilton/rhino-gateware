from migen.fhdl.std import *
from migen.bus import csr

# TODO: rewrite in full FHDL
# TODO: support streams

class GPMC(Module):
	def __init__(self, gpmc_pads, csr_cs_pad, dma_cs_pad, dmareq_pads, streams_from, streams_to):
		assert(csr.data_width == 16)
		self.csr = csr.Interface()
		
		if dmareq_pads or streams_from or streams_to:
			raise NotImplementedError

		###

		self.specials += Instance("gpmc",
			Instance.Input("sys_clk", ClockSignal()),
			Instance.Input("sys_rst", ResetSignal()),
			
			Instance.Output("csr_adr", self.csr.adr),
			Instance.Output("csr_we", self.csr.we),
			Instance.Output("csr_dat_w", self.csr.dat_w),
			Instance.Input("csr_dat_r", self.csr.dat_r),
			
			Instance.Input("gpmc_clk", gpmc_pads.clk),
			Instance.Input("gpmc_a", gpmc_pads.a),
			Instance.Input("gpmc_we_n", gpmc_pads.we_n),
			Instance.Input("gpmc_oe_n", gpmc_pads.oe_n),
			Instance.Input("gpmc_ale_n", gpmc_pads.ale_n),
			Instance.Input("gpmc_csr_cs_n", csr_cs_pad),
			Instance.InOut("gpmc_d", gpmc_pads.d))

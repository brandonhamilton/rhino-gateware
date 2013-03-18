from migen.fhdl.structure import *
from migen.fhdl.specials import Instance
from migen.bus import csr

# TODO: rewrite in full FHDL
# TODO: support streams

class GPMC:
	def __init__(self, gpmc_pins, csr_cs_pin, dma_cs_pin, dmareq_pins, streams_from, streams_to):
		self._gpmc_pins = gpmc_pins
		self._csr_cs_pin = csr_cs_pin
		self._dma_cs_pin = dma_cs_pin
		self._dmareq_pins = dmareq_pins
		self._streams_from = streams_from
		self._streams_to = streams_to
		
		assert(csr.data_width == 16)
		self.csr = csr.Interface()
		
		if self._dmareq_pins or self._streams_from or self._streams_to:
			raise NotImplementedError

	def get_fragment(self):
		inst = Instance("gpmc",
			Instance.Input("sys_clk", ClockSignal()),
			Instance.Input("sys_rst", ResetSignal()),
			
			Instance.Output("csr_adr", self.csr.adr),
			Instance.Output("csr_we", self.csr.we),
			Instance.Output("csr_dat_w", self.csr.dat_w),
			Instance.Input("csr_dat_r", self.csr.dat_r),
			
			Instance.Input("gpmc_clk", self._gpmc_pins.clk),
			Instance.Input("gpmc_a", self._gpmc_pins.a),
			Instance.Input("gpmc_we_n", self._gpmc_pins.we_n),
			Instance.Input("gpmc_oe_n", self._gpmc_pins.oe_n),
			Instance.Input("gpmc_ale_n", self._gpmc_pins.ale_n),
			Instance.Input("gpmc_csr_cs_n", self._csr_cs_pin),
			Instance.InOut("gpmc_d", self._gpmc_pins.d)
		)
		return Fragment(specials={inst})

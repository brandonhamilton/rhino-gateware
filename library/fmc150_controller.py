from migen.fhdl.structure import *
from library.gpio import *
from library.uid import UID_FMC150_CTRL

class FMC150Controller(GPIO):
	def __init__(self, baseapp, csr_name="fmc150_controller"):
		fc = baseapp.constraints.request("fmc150_ctrl")
		signals = [
			(fc.spi_sclk,		OUTPUT,	"spi_sclk"),
			(fc.spi_data,		OUTPUT,	"spi_data"),
			
			(fc.adc_sdo,		INPUT,	"adc_sdo"),
			(fc.adc_en_n,		OUTPUT,	"adc_en_n"),
			(fc.adc_reset,		OUTPUT,	"adc_reset"),
			
			(fc.cdce_sdo,		INPUT,	"cdce_sdo"),
			(fc.cdce_en_n,		OUTPUT,	"cdce_en_n"),
			(fc.cdce_reset_n,	OUTPUT,	"cdce_reset_n"),
			(fc.cdce_pd_n,		OUTPUT,	"cdce_pd_n"),
			(fc.cdce_pll_status,	INPUT,	"cdce_pll_status"),
			(fc.cdce_ref_en, 	OUTPUT,	"cdce_ref_en"),
			
			(fc.dac_sdo,		INPUT,	"dac_sdo"),
			(fc.dac_en_n,		OUTPUT,	"dac_en_n"),
			
			(fc.mon_sdo,		INPUT,	"mon_sdo"),
			(fc.mon_en_n,		OUTPUT,	"mon_en_n"),
			(fc.mon_reset_n,	OUTPUT,	"mon_reset_n")
		]
		self.fmc150_ctrl = fc
		GPIO.__init__(self, baseapp, csr_name, UID_FMC150_CTRL, signals)

	def get_fragment(self):
		comb = [
			self.fmc150_ctrl.pg_c2m.eq(1)
		]
		return GPIO.get_fragment(self) + Fragment(comb)

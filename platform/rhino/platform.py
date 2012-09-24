from migen.fhdl.structure import *
from migen.fhdl import verilog

from tools.cmgr import *
from tools.mmgr import *
from library.gpmc import *
from library.crg import *

# set CSR data width to 16-bit
from migen.bus import csr
csr.data_width = 16

TARGET_VENDOR = "xilinx"
TARGET_DEVICE = "xc6slx150t-fgg676-3"

PLATFORM_RESOURCES = [
	("user_led", 0, Pins("Y3")),
	("user_led", 1, Pins("Y1")),
	("user_led", 2, Pins("W2")),
	("user_led", 3, Pins("W1")),
	("user_led", 4, Pins("V3")),
	("user_led", 5, Pins("V1")),
	("user_led", 6, Pins("U2")),
	("user_led", 7, Pins("U1")),
	
	("clk100", 0,
		Subsignal("p", Pins("B14"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
		Subsignal("n", Pins("A14"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE"))
	),
	
	("gpio", 0, Pins("R8")),
	
	("gpmc", 0, 
		Subsignal("clk", Pins("R26")),
		Subsignal("a", Pins("N17", "N18", "L23", "L24", "N19", "N20", "N21", "N22", "P17", "P19")),
		Subsignal("d", Pins("N23", "N24", "R18", "R19", "P21", "P22", "R20", "R21", "P24", "P26", "R23", "R24", "T22", "T23", "U23", "R25")),
		Subsignal("we_n", Pins("W26")),
		Subsignal("oe_n", Pins("AA25")),
		Subsignal("ale_n", Pins("AA26")),
		IOStandard("LVCMOS33")),
	# Warning: CS are numbered 1-7 on ARM side and 0-6 on FPGA side.
	# Numbers here are given on the FPGA side.
	("gpmc_ce_n", 0, Pins("V23"), IOStandard("LVCMOS33")), # nCS0
	("gpmc_ce_n", 1, Pins("U25"), IOStandard("LVCMOS33")), # nCS1
	("gpmc_ce_n", 2, Pins("W25"), IOStandard("LVCMOS33")), # nCS6
	("gpmc_dmareq_n", 0, Pins("T24"), IOStandard("LVCMOS33")), # nCS2
	("gpmc_dmareq_n", 1, Pins("T26"), IOStandard("LVCMOS33")), # nCS3
	("gpmc_dmareq_n", 2, Pins("V24"), IOStandard("LVCMOS33")), # nCS4
	("gpmc_dmareq_n", 3, Pins("V26"), IOStandard("LVCMOS33")), # nCS5
	
	# FMC150
	("fmc150_ctrl", 0,
		Subsignal("spi_sclk", Pins("AE5")),
		Subsignal("spi_data", Pins("AF5")),
		
		Subsignal("adc_sdo", Pins("U13")),
		Subsignal("adc_en_n", Pins("AA15")),
		Subsignal("adc_reset", Pins("V13")),
		
		Subsignal("cdce_sdo", Pins("AA8")),
		Subsignal("cdce_en_n", Pins("Y9")),
		Subsignal("cdce_reset_n", Pins("AB7")),
		Subsignal("cdce_pd_n", Pins("AC6")),
		Subsignal("cdce_pll_status", Pins("W7")),
		Subsignal("cdce_ref_en", Pins("W8")),
		
		Subsignal("dac_sdo", Pins("W9")),
		Subsignal("dac_en_n", Pins("W10")),
		
		Subsignal("mon_sdo", Pins("AC5")),
		Subsignal("mon_en_n", Pins("AD6")),
		Subsignal("mon_reset_n", Pins("AF6")),
		Subsignal("mon_int_n", Pins("AD5")),
		
		Subsignal("pg_c2m", Pins("AA23"), IOStandard("LVCMOS33"))
	),
	("fmc150_dac", 0,
		Subsignal("dat_p", Pins("AA10", "AA9", "V11", "Y11", "W14", "Y12", "AD14", "AE13"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
		Subsignal("dat_n", Pins("AB11", "AB9", "V10", "AA11", "Y13", "AA12", "AF14", "AF13"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
		Subsignal("frame_p", Pins("AB13"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
		Subsignal("frame_n", Pins("AA13"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
		Subsignal("txenable", Pins("AB15"), IOStandard("LVCMOS25"))
	),
	("fmc150_adc", 0,
		Subsignal("dat_a_p", Pins("AB14", "Y21", "W20", "AB22", "V18", "W17", "AA21")),
		Subsignal("dat_a_n", Pins("AC14", "AA22", "Y20", "AC22", "W19", "W18", "AB21")),
		Subsignal("dat_b_p", Pins("Y17", "U15", "AA19", "W16", "AA18", "Y15", "V14")),
		Subsignal("dat_b_n", Pins("AA17", "V16", "AB19", "Y16", "AB17", "AA16", "V15")),
		IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")
	),
	("fmc150_clocks", 0,
		Subsignal("dac_clk_p", Pins("V12"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
		Subsignal("dac_clk_n", Pins("W12"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
		Subsignal("adc_clk_p", Pins("AE15"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
		Subsignal("adc_clk_n", Pins("AF15"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
		Subsignal("clk_to_fpga", Pins("W24"), IOStandard("LVCMOS25"))
	),
	
	("fmc150_ext_trigger", 0, Pins("U26")),
]

CSR_BASE = 0x08000000
DMA_BASE = 0x10000000
DMA_PORT_RANGE = 8192

class BaseApp:
	def __init__(self, components):
		self.constraints = ConstraintManager(PLATFORM_RESOURCES)
		self.csrs = CSRManager()
		self.streams = StreamManager(16)
		
		self.crg = None
		self.components_inst = []
		for c in components:
			if isinstance(c, tuple):
				inst = c[0](self, **c[1])
			else:
				inst = c(self)
			self.components_inst.append(inst)
			if isinstance(inst, CRG):
				self.crg = inst

		# default clock and reset generator
		if self.crg is None:
			self.crg = CRG100(self)
			self.components_inst.append(self.crg)
	
	def get_fragment(self):
		streams_from = self.streams.get_ports(FROM_EXT)
		streams_to = self.streams.get_ports(TO_EXT)
		s_count = len(streams_from) + len(streams_to)
		dmareq_pins = [self.constraints.request("gpmc_dmareq_n", i) for i in range(s_count)]
		gpmc_bridge = GPMC(self.constraints.request("gpmc"),
			self.constraints.request("gpmc_ce_n", 0),
			self.constraints.request("gpmc_ce_n", 1),
			dmareq_pins,
			streams_from, streams_to)
		self.csrs.master = gpmc_bridge.csr
		
		return self.csrs.get_fragment() + \
			gpmc_bridge.get_fragment() + \
			sum([c.get_fragment() for c in self.components_inst], Fragment())
	
	def get_symtab(self):
		return self.csrs.get_symtab(CSR_BASE) + \
			self.streams.get_symtab(DMA_BASE, DMA_PORT_RANGE)
	
	def get_formatted_symtab(self):
		symtab = self.get_symtab()
		r = ""
		for s in symtab:
			r += "{}\t{}\t0x{:08x}\t0x{:x}\n".format(*s)
		return r
	
	def get_source(self):
		f = self.get_fragment()
		symtab = self.get_formatted_symtab()
		vsrc, ns = verilog.convert(f,
			self.constraints.get_io_signals(),
			clock_domains=self.crg.get_clock_domains(),
			return_ns=True)
		sig_constraints = self.constraints.get_sig_constraints()
		return vsrc, ns, sig_constraints, symtab

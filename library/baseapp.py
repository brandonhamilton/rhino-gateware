from migen.fhdl import verilog

from tools.cmgr import *
from tools.mmgr import *
from library.gpmc import *
from library.crg import *

# set CSR data width to 16-bit
from migen.bus import csr
csr.data_width = 16

CSR_BASE = 0x08000000
DMA_BASE = 0x10000000
DMA_PORT_RANGE = 8192

class GenericBaseApp:
	def __init__(self, components, platform_resources, crg_factory=lambda app: CRG100(app)):
		self.platform_resources = platform_resources
		
		self.constraints = ConstraintManager(self.platform_resources)
		self.csrs = CSRManager()
		self.streams = StreamManager(16)
		
		self.components_inst = []
		
		# clock and reset generator
		self.crg = crg_factory(self)
		self.components_inst.append(self.crg)
		
		for c in components:
			if isinstance(c, tuple):
				inst = c[0](self, **c[1])
			else:
				inst = c(self)
			self.components_inst.append(inst)
	
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
		platform_commands = self.constraints.get_platform_commands()
		return vsrc, ns, sig_constraints, platform_commands, symtab

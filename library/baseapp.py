import os
import subprocess

from migen.fhdl import verilog
from mibuild.tools import write_to_file

from tools.mmgr import *
from library.gpmc import *
from library.crg import *

# set CSR data width to 16-bit
from migen.bus import csr
csr.data_width = 16

CSR_BASE = 0x08000000
DMA_BASE = 0x10000000
DMA_PORT_RANGE = 8192

class Comp:
	def __init__(self, comp_class, name=None, platform=None, **comp_params):
		self.comp_class = comp_class
		self.comp_params = comp_params
		self.name = name
		self.platform = platform

class GenericBaseApp:
	def __init__(self, components, mplat, mkbof_hwrtyp, crg_factory):
		self.mplat = mplat
		self.mkbof_hwrtyp = mkbof_hwrtyp
		
		self.components = dict()
		self.all_components = []
		
		# clock and reset generator
		self.crg = crg_factory(self)
		self.all_components.append(self.crg)
		
		for c in components:
			if not isinstance(c, Comp):
				c = Comp(c)
			if c.platform is None or c.platform == mplat.name:
				self.current_comp_name = c.name
				inst = c.comp_class(self, **c.comp_params)
				del self.current_comp_name
				if c.name is not None:
					self.components[c.name] = inst
				self.all_components.append(inst)
	
	def get_formatted_symtab(self):
		symtab = self.get_symtab()
		r = ""
		for s in symtab:
			r += "{}\t{}\t0x{:08x}\t0x{:x}\n".format(*s)
		return r

	def build(self):
		f = self.get_fragment()
		clock_domains = self.crg.get_clock_domains()
		self.mplat.build(f,	clock_domains=clock_domains)

		symtab = self.get_formatted_symtab()
		os.chdir("build")
		build_name = "top"
		write_to_file(build_name + ".symtab", symtab)
		r = subprocess.call(["mkbof",
			"-t", str(self.mkbof_hwrtyp),
			"-s", build_name + ".symtab",
			"-o", build_name + ".bof",
			build_name + ".bin"])
		if r != 0:
			raise OSError("mkbof failed")
		os.chdir("..")

class RhinoBaseApp(GenericBaseApp):
	def __init__(self, components, mplat, mkbof_hwrtyp, crg_factory=lambda app: CRG100(app)):
		self.csrs = CSRManager()
		self.streams = StreamManager(16)
		GenericBaseApp.__init__(self, components, mplat, mkbof_hwrtyp, crg_factory)
	
	def get_fragment(self):
		streams_from = self.streams.get_ports(FROM_EXT)
		streams_to = self.streams.get_ports(TO_EXT)
		s_count = len(streams_from) + len(streams_to)
		dmareq_pins = [self.mplat.request("gpmc_dmareq_n", i) for i in range(s_count)]
		gpmc_bridge = GPMC(self.mplat.request("gpmc"),
			self.mplat.request("gpmc_ce_n", 0),
			self.mplat.request("gpmc_ce_n", 1),
			dmareq_pins,
			streams_from, streams_to)
		self.csrs.master = gpmc_bridge.csr
		
		return self.csrs.get_fragment() + \
			gpmc_bridge.get_fragment() + \
			sum([c.get_fragment() for c in self.all_components], Fragment())
	
	def get_symtab(self):
		return self.csrs.get_symtab(CSR_BASE) + \
			self.streams.get_symtab(DMA_BASE, DMA_PORT_RANGE)

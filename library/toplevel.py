import os, stat, subprocess
from itertools import count

from migen.fhdl import verilog
from migen.bank import csrgen
from migen.bank.description import *
from migen.bus import csr
from mibuild.tools import write_to_file

from library.gpmc import GPMC

# set CSR data width to 16-bit
csr.data_width = 16

BOF_PERM_READ = 0x01
BOF_PERM_WRITE = 0x02

class GenericToplevel(Module):
	def __init__(self, mkbof_hwrtyp, mibuild_platform, app_toplevel_class):
		self.mkbof_hwrtyp = mkbof_hwrtyp
		self.mibuild_platform = mibuild_platform

		self.submodules.app = app_toplevel_class(self.mibuild_platform)
		adr_map = count()
		self.submodules.csrbankarray = csrgen.BankArray(self.app, lambda name, memory: next(adr_map))
	
	def get_symtab(self):
		raise NotImplementedError("GenericToplevel.get_symtab must be overloaded")

	def get_formatted_symtab(self):
		symtab = self.get_symtab()
		r = ""
		for s in symtab:
			r += "{}\t{}\t0x{:08x}\t0x{:x}\n".format(*s)
		return r

	def build(self):
		self.mibuild_platform.build(self.get_fragment())
		symtab = self.get_formatted_symtab()
		os.chdir("build")
		build_name = "top"
		write_to_file(build_name + ".symtab", symtab)
		bof_name = build_name + ".bof"
		r = subprocess.call(["mkbof",
			"-t", str(self.mkbof_hwrtyp),
			"-s", build_name + ".symtab",
			"-o", bof_name,
			build_name + ".bin"])
		if r != 0:
			raise OSError("mkbof failed")
		st = os.stat(bof_name)
		os.chmod(bof_name, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
		os.chdir("..")

class GPMCToplevel(GenericToplevel):
	def __init__(self, *args, **kwargs):
		GenericToplevel.__init__(self, *args, **kwargs)

		self.submodules.gpmc_bridge = GPMC(
			self.mibuild_platform.request("gpmc"),
			self.mibuild_platform.request("gpmc_ce_n", 0),
			self.mibuild_platform.request("gpmc_ce_n", 1),
			[],	[], [])
		self.submodules.csrcon = csr.Interconnect(self.gpmc_bridge.csr, self.csrbankarray.get_buses())
	
	def get_symtab(self):
		csr_base = 0x08000000
		csr_bank_size = 0x400
		symtab = []
		for name, csrs, mapaddr, rmap in self.csrbankarray.banks:
			reg_base = csr_base + csr_bank_size*mapaddr
			for c in csrs:
				if isinstance(c, (CSR, CSRStorage)):
					permission = BOF_PERM_WRITE|BOF_PERM_READ
				else:
					permission = BOF_PERM_READ
				length = 2*((csr.data_width - 1 + c.size)//csr.data_width)
				symtab.append((name + "_" + c.name, permission, reg_base, length))
				reg_base += length
		for name, memory, mapaddr, mmap in self.csrbankarray.srams:
			mem_base = csr_base + csr_bank_size*mapaddr
			if not hasattr(memory, "bus_read_only") or not memory.bus_read_only:
				permission = BOF_PERM_WRITE|BOF_PERM_READ
			else:
				permission = BOF_PERM_READ
			length = min(2*memory.depth, csr_bank_size)
			symtab.append((name + "_" + memory.name_override, permission, mem_base, length))
		return symtab

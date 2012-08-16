from migen.bus import csr
from migen.bank.description import *
from migen.bank.csrgen import Bank

from library.uid import UID

BOF_PERM_READ = 0x01
BOF_PERM_WRITE = 0x02

class CSRManager:
	def __init__(self):
		self.banks = []
		self.master = None
	
	def request(self, name, uid, *registers):
		uid_inst = UID(uid)
		all_registers = uid_inst.get_registers() + list(registers)
		self.banks.append((name, all_registers, uid_inst))
	
	def get_fragment(self):
		csr_f = Fragment()
		csr_ifs = []
		for address, (name, registers, uid_inst) in enumerate(self.banks):
			bank = Bank(registers, address)
			csr_ifs.append(bank.interface)
			csr_f += uid_inst.get_fragment() + bank.get_fragment()
		assert(self.master is not None)
		csr_ic = csr.Interconnect(self.master, csr_ifs)
		return csr_f + csr_ic.get_fragment()
	
	def get_symtab(self, base):
		symtab = []
		for name, registers, uid_inst in self.banks:
			offset = 0
			for register in registers:
				if isinstance(register, RegisterRaw):
					permission = BOF_PERM_READ|BOF_PERM_WRITE
				else:
					permission = 0
					for f in register.fields:
						if (f.access_bus == READ_ONLY) or (f.access_bus == READ_WRITE):
							permission |= BOF_PERM_READ
						if (f.access_bus == WRITE_ONLY) or (f.access_bus == READ_WRITE):
							permission |= BOF_PERM_WRITE
				if isinstance(register, RegisterRaw):
					nbits = register.size
				else:
					nbits = sum([f.size for f in register.fields])
				length = 2*((7 + nbits)//8)
				symtab.append((name + "_" + register.name, permission, base + offset, length))
				offset += length
			base += 0x400
		return symtab

(FROM_EXT, TO_EXT) = range(2)

class StreamPort:
	def __init__(self, data_width):
		self.data = Signal(BV(data_width))
		self.stb = Signal()
		self.ack = Signal()
		
class StreamManager:
	def __init__(self, data_width):
		self.data_width = data_width
		self.streams = []
	
	def request(self, name, direction):
		port = StreamPort(self.data_width)
		self.streams.append((name, direction, port))
		return port
	
	def get_ports(self, direction):
		return [s[2] for s in self.streams if s[1] == direction]
	
	def get_symtab(self, base, port_range):
		r = []
		for name, direction, port in self.streams:
			if direction == FROM_EXT:
				r.append((name, BOF_PERM_WRITE, base, port_range))
				base += port_range
		for name, direction, port in self.streams:
			if direction == TO_EXT:
				r.append((name, BOF_PERM_READ, base, port_range))
				base += port_range
		return r

from migen.bus import csr
from migen.bank.description import *
from migen.bank import csrgen

from library.uid import UID
from library import opb

BOF_PERM_READ = 0x01
BOF_PERM_WRITE = 0x02

class CSRManager:
	def __init__(self):
		self.slots = []
		self.master = None
	
	def request(self, name, uid, *registers, memories=[]):
		uid_inst = UID(uid)
		all_registers = uid_inst.get_registers() + list(registers)
		
		start_addr = len(self.slots)
		memory_slots = []
		for offset, memory in enumerate(memories):
			access = csr.SRAM(memory, start_addr + 1 + offset)
			all_registers += access.get_registers()
			memory_slots.append((name, memory, [access]))
			
		bank = csrgen.Bank(all_registers, start_addr)
		self.slots.append((name, all_registers, [bank, uid_inst]))
		self.slots += memory_slots
	
	def get_fragment(self):
		csr_f = Fragment()
		csr_ifs = []
		for address, (name, what, instances) in enumerate(self.slots):
			csr_ifs.append(instances[0].bus)
			csr_f = sum([i.get_fragment() for i in instances], csr_f)
		assert(self.master is not None)
		csr_ic = csr.Interconnect(self.master, csr_ifs)
		return csr_f + csr_ic.get_fragment()
	
	def get_symtab(self, base):
		symtab = []
		for name, what, instances in self.slots:
			if isinstance(what, Memory):
				symtab.append((name + "_mem", BOF_PERM_READ|BOF_PERM_WRITE, base, min(what.depth, 0x400)))
			else:
				offset = 0
				for register in what:
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
					length = 2*((csr.data_width - 1 + nbits)//csr.data_width)
					symtab.append((name + "_" + register.name, permission, base + offset, length))
					offset += length
			base += 0x400
		return symtab

(FROM_EXT, TO_EXT) = range(2)

class StreamPort:
	def __init__(self, data_width):
		self.data = Signal(data_width)
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

class OPBManager:
	def __init__(self, baseapp, baseaddr):
		self.baseapp = baseapp
		self.next_address = baseaddr
		self.slots = []
	
	def request(self, aperture, name=None):
		if name is None:
			name = self.baseapp.current_comp_name
		if name is None:
			raise ValueError("Anonymous components are not allowed on the OPB")
		
		address = self.next_address
		self.next_address += aperture
		bus = opb.Interface()
		
		self.slots.append((name, bus, address, aperture))
		return bus, address
		
	def get_symtab(self):
		r = []
		for name, bus, address, aperture in self.slots:
			r.append((name, BOF_PERM_READ|BOF_PERM_WRITE, address, aperture))
		return r
	
	def get_fragment(self):
		intercon = Interconnect(self.master, [slot[1] for slot in self.slots])
		return intercon.get_fragment()

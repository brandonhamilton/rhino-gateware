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
                symtab.append((name + "_" + register.name, permission, base, length))
                base += length
        return symtab

(FROM_EXT, TO_EXT) = range(2)
        
class StreamManager:
    def __init__(self, data_width):
        pass
    
    def request(self, name, direction):
        pass
    
    def get_ports(self, direction):
        return []
    
    def get_fragment(self):
        return Fragment()
    
    def get_symtab(self, base):
        return []

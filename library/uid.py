from migen.fhdl.structure import *
from migen.bank.description import *

MAGIC = 0xc2d5e717

UID_LED_CONTROLLER = 1

class UID:
    def __init__(self, uid):
        self.uid = uid
        self.reg_magic = RegisterField("magic", 32, READ_ONLY, WRITE_ONLY)
        self.reg_uid = RegisterField("uid", 32, READ_ONLY, WRITE_ONLY)
    
    def get_registers(self):
        return [self.reg_magic, self.reg_uid]
    
    def get_fragment(self):
        comb = [
            self.reg_magic.field.w.eq(MAGIC),
            self.reg_uid.field.w.eq(self.uid)
        ]
        return Fragment(comb)

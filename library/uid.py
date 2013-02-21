from migen.fhdl.structure import *
from migen.bank.description import *

MAGIC = 0xc2d5e717

UID_LED_CONTROLLER = 1
UID_DEMO_AFFINE = 2
UID_FMC150_CTRL = 3
UID_CRG_RADAR = 4
UID_WAVEFORM_GENERATOR = 5
UID_WAVEFORM_COLLECTOR = 6

# 0x100 to 0x1ff are Vermeer components
UID_VERMEER = 0x100

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

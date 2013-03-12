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
		self._r_magic = RegisterField(32, READ_ONLY, WRITE_ONLY)
		self._r_uid = RegisterField(32, READ_ONLY, WRITE_ONLY)
	
	def get_registers(self):
		return [self._r_magic, self._r_uid]
	
	def get_fragment(self):
		comb = [
			self._r_magic.field.w.eq(MAGIC),
			self._r_uid.field.w.eq(self.uid)
		]
		return Fragment(comb)

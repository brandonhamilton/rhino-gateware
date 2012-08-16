from migen.fhdl.structure import *
from migen.bank.description import *

from library.uid import UID_LED_CONTROLLER

class LedController:
	def __init__(self, baseapp, count, csr_name="led_controller", led_name="user_led"):
		self.reg_leds = RegisterField("leds", count)
		baseapp.csrs.request(csr_name, UID_LED_CONTROLLER, self.reg_leds)
		self.led_signals = [baseapp.constraints.request(led_name) for i in range(count)]
	
	def get_fragment(self):
		comb = [Cat(*self.led_signals).eq(self.reg_leds.field.r)]
		return Fragment(comb)

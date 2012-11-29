from library.gpio import *
from library.uid import UID_LED_CONTROLLER

class LedController(GPIO):
	def __init__(self, baseapp, count, csr_name="led_controller", led_name="user_led"):
		signals = [(baseapp.constraints.request(led_name), OUTPUT, "led"+str(i))
			for i in range(count)]
		super().__init__(baseapp, csr_name, UID_LED_CONTROLLER, signals)

class LedBlinker:
	def __init__(self, baseapp, divbits=26, led_name="user_led"):
		self._led = baseapp.constraints.request(led_name)
		self._divbits = divbits
	
	def get_fragment(self):
		counter = Signal(self._divbits)
		comb = [
			self._led.eq(counter[self._divbits-1])
		]
		sync = [
			counter.eq(counter + 1)
		]
		return Fragment(comb, sync)

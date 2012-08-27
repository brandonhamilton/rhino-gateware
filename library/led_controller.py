from library.gpio import *
from library.uid import UID_LED_CONTROLLER

class LedController(GPIO):
	def __init__(self, baseapp, count, csr_name="led_controller", led_name="user_led"):
		signals = [(baseapp.constraints.request(led_name), OUTPUT, "led"+str(i))
			for i in range(count)]
		super().__init__(baseapp, csr_name, UID_LED_CONTROLLER, signals)

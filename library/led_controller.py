from migen.fhdl.structure import *
from migen.bank.description import *
from migen.bank.csrgen import *

from library.uid import UID, UID_LED_CONTROLLER

class LedController:
    def __init__(self, baseapp, count, csr_name="led_controller", led_name="user_led"):
        self.uid = UID(UID_LED_CONTROLLER)
        self.reg_leds = RegisterField("leds", count)
        address, interface = baseapp.request_csr(csr_name)
        self.bank = Bank(self.uid.get_registers() + [self.reg_leds], address, interface)
        self.led_signals = [baseapp.cm.request(led_name) for i in range(count)]
    
    def get_fragment(self):
        comb = [Cat(*self.led_signals).eq(self.reg_leds.field.r)]
        return self.uid.get_fragment() + self.bank.get_fragment() + Fragment(comb)

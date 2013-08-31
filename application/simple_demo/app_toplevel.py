from migen.fhdl.std import *
from migen.bank.description import AutoCSR

from components.crg import CRGDiffBasic
from components.gpio import Blinker, GPIOOut

class AppToplevel(Module, AutoCSR):
	def __init__(self, stl):
		platform = stl.mibuild_platform
		if platform.name == "rhino":
			self.submodules.crg = CRGDiffBasic(platform, platform.request("clk100"))
		elif platform.name == "molerad":
			self.submodules.crg = CRGDiffBasic(platform, platform.request("clk96"), 10.416)
		else:
			raise NotImplementedError("Unsupported platform: "+platform.name)

		self.submodules.blinker = Blinker(platform.request("user_led"))
		self.submodules.leds = GPIOOut(Cat(*[platform.request("user_led") for i in range(3)]))

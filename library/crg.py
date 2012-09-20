from migen.fhdl.structure import *

class CRG:
	pass

class CRG100(CRG):
	def __init__(self, baseapp):
		self.cd = ClockDomain("sys")
		self._clk = baseapp.constraints.request("clk100")
		self._rst = baseapp.constraints.request("gpio", 0)

	def get_fragment(self):
		comb = [
			self.cd.rst.eq(self._rst)
		]
		inst = Instance("IBUFGDS",
			Instance.Input("I", self._clk.p),
			Instance.Input("IB", self._clk.n),
			Instance.Output("O", self.cd.clk)
		)
		return Fragment(comb, instances=[inst])

from migen.fhdl.structure import *
from migen.bank.description import *

from library.mmgr import *
from library.uid import UID_DEMO_AFFINE

class DemoAffine:
	def __init__(self, baseapp, pipeline_depth=3,
	  stream_from_name="affine_in", stream_to_name="affine_out",
	  csr_name="affine"):
		self.pipeline_depth = pipeline_depth
		self.port_in = baseapp.streams.request(stream_from_name, FROM_EXT)
		self.port_out = baseapp.streams.request(stream_to_name, TO_EXT)
		width = len(self.port_in.data)
		self._r_a = RegisterField(width)
		self._r_b = RegisterField(width)
		baseapp.csrs.request(csr_name, UID_DEMO_AFFINE, self._r_a, self._r_b)
		
	def get_fragment(self):
		width = len(self.port_in.data)
		
		pmac = []
		result = self._r_a.field.r*self.port_in.data + self._r_b.field.r
		for stage in range(self.pipeline_depth):
			iresult = Signal(width)
			pmac.append(iresult.eq(result))
			result = iresult
		
		en = Signal()
		valid = Signal(self.pipeline_depth)
		sync = [
			If(en, *pmac),
			If(en, valid.eq(Cat(valid[1:], self.port_in.stb)))
		]
		comb = [
			self.port_out.stb.eq(valid[0]),
			self.port_out.data.eq(result),
			self.port_in.ack.eq(en),
			en.eq(self.port_out.ack | ~valid[0])
		]
			
		return Fragment(comb, sync)

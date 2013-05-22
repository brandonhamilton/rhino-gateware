from math import sin, cos, pi

from migen.fhdl.std import *
from migen.genlib.complex import *

class _Butterfly:
	def __init__(self, nbits, nfrac, latency):
		self.nbits = nbits
		self.nfrac = nfrac
		self.latency = latency
		
		self.A = SignalC(self.nbits)
		self.B = SignalC(self.nbits)
		self.w = SignalC(self.nbits) # FIXME
		self.C = SignalC(self.nbits + 2)
		self.D = SignalC(self.nbits + 2)

	def get_fragment(self):
		sC = SignalC(self.nbits + 2)
		sD = SignalC(self.nbits + 2)
		Bw = SignalC(2*self.nbits + 1 - self.nfrac)
		comb = [
			Bw.eq(self.B*self.w >> self.nfrac),
			sC.eq(self.A + Bw),
			sD.eq(self.A - Bw)
		]
		sync = []
		for i in range(self.latency):
			tC = SignalC(self.nbits + 2)
			tD = SignalC(self.nbits + 2)
			sync += [
				tC.eq(sC),
				tD.eq(sD)
			]
			sC = tC
			sD = tD
		comb += [
			self.C.eq(sC),
			self.D.eq(sD)
		]
		return Fragment(comb, sync)

def _twiddle(i, N, nfrac):
	real = cos(2.0*pi*i/N)
	imag = sin(2.0*pi*i/N)
	scale = 2**nfrac
	return Complex(int(real*scale), int(imag*scale))

class _BiplexStage:
	def __init__(self, N, nbits, nfrac, butterfly_latency):
		self.nbits = nbits
		
		self.dat_i0 = SignalC(self.nbits)
		self.dat_i1 = SignalC(self.nbits)
		self.dat_o0 = SignalC(self.nbits)
		self.dat_o1 = SignalC(self.nbits)
	
	def get_fragment(self):
		...

class BiplexFFT:
	def __init__(self, N, nbits, nfrac, butterfly_latency=3):
		...
	
	def get_fragment(self):
		...

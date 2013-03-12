from migen.fhdl.structure import *
from migen.bank.description import *

(INPUT, OUTPUT) = range(2)

# signals is a list of triples (signal, INPUT/OUTPUT, name)
class GPIO:
	def __init__(self, baseapp, csr_name, uid, signals):
		self.signals = signals
		self.fields = []
		for signal, direction, name in self.signals:
			if direction == INPUT:
				self.fields.append(Field(len(signal), READ_ONLY, WRITE_ONLY, name=name))
			elif direction == OUTPUT:
				self.fields.append(Field(len(signal), READ_WRITE, READ_ONLY, name=name))
			else:
				raise TypeError
		r_gpio = RegisterFields(*self.fields)
		baseapp.csrs.request(csr_name, uid, r_gpio)
	
	def get_fragment(self):
		comb = []
		for (signal, direction, name), field in zip(self.signals, self.fields):
			if direction == INPUT:
				comb.append(field.w.eq(signal))
			elif direction == OUTPUT:
				comb.append(signal.eq(field.r))
			else:
				raise TypeError
		return Fragment(comb)

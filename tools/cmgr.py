from migen.fhdl.structure import *
from migen.corelogic.record import Record

class ConstraintError(Exception):
	pass
	
class Pins:
	def __init__(self, *identifiers):
		self.identifiers = identifiers

class IOStandard:
	def __init__(self, name):
		self.name = name

class Drive:
	def __init__(self, strength):
		self.strength = strength

class Misc:
	def __init__(self, misc):
		self.misc = misc

class Subsignal:
	def __init__(self, name, *constraints):
		self.name = name
		self.constraints = list(constraints)

def _lookup(description, name, number):
	for resource in description:
		if resource[0] == name and (number is None or resource[1] == number):
			return resource
	return ConstraintError("Resource not found")
		
def _resource_type(resource):
	t = None
	for element in resource[2:]:
		if isinstance(element, Pins):
			assert(t is None)
			t = BV(len(element.identifiers))
		elif isinstance(element, Subsignal):
			if t is None:
				t = []
			assert(isinstance(t, list))
			n_bits = None
			for c in element.constraints:
				if isinstance(c, Pins):
					assert(n_bits is None)
					n_bits = len(c.identifiers)
			t.append((element.name, BV(n_bits)))
	return t

def _match(description, requests):
	available = list(description)
	matched = []
	
	# 1. Match requests for a specific number
	for request in requests:
		if request[1] is not None:
			resource = _lookup(available, request[0], request[1])
			available.remove(resource)
			matched.append((resource, request[2]))
			
	# 2. Match requests for no specific number
	for request in requests:
		if request[1] is None:
			resource = _lookup(available, request[0], request[1])
			available.remove(resource)
			matched.append((resource, request[2]))
	
	return matched

def _separate_pins(constraints):
	pins = None
	others = []
	for c in constraints:
		if isinstance(c, Pins):
			assert(pins is None)
			pins = c.identifiers
		else:
			others.append(c)
	return pins, others
	
class ConstraintManager:
	def __init__(self, description):
		self.description = description
		self.requests = []
		self.platform_commands = []
		
	def request(self, name, number=None, obj=None):
		r = _lookup(self.description, name, number)
		t = _resource_type(r)
		
		# If obj is None, then create it.
		# If it already exists, do some sanity checking.
		if obj is None:
			if isinstance(t, BV):
				obj = Signal(t, name_override=r[0])
			else:
				obj = Record(t)
		else:
			if isinstance(t, BV):
				assert(isinstance(obj, Signal) and obj.bv == t)
			else:
				for e in t:
					sig = getattr(obj, e[0])
					assert(isinstance(sig, Signal) and sig.bv == e[1])

		# Register the request
		self.requests.append((name, number, obj))
		
		return obj
	
	def add_platform_command(self, command, **signals):
		self.platform_commands.append((command, signals))
	
	def get_io_signals(self):
		s = set()
		for req in self.requests:
			obj = req[2]
			if isinstance(obj, Signal):
				s.add(obj)
			else:
				for k in obj.__dict__:
					p = getattr(obj, k)
					if isinstance(p, Signal):
						s.add(p)
		return s
	
	def get_sig_constraints(self):
		r = []
		matched = _match(self.description, self.requests)
		for resource, obj in matched:
			name = resource[0]
			number = resource[1]
			has_subsignals = False
			top_constraints = []
			for element in resource[2:]:
				if isinstance(element, Subsignal):
					has_subsignals = True
				else:
					top_constraints.append(element)
			if has_subsignals:
				for element in resource[2:]:
					if isinstance(element, Subsignal):
						sig = getattr(obj, element.name)
						pins, others = _separate_pins(top_constraints + element.constraints)
						r.append((sig, pins, others, (name, number, element.name)))
			else:
				pins, others = _separate_pins(top_constraints)
				r.append((obj, pins, others, (name, number, None)))
		return r

	def get_platform_commands(self):
		return self.platform_commands

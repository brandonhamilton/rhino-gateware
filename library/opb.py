from migen.fhdl.structure import *
from migen.bus.simple import *

class Interface(SimpleInterface):
	def __init__(self):
		SimpleInterface.__init__(self, Description(
			(M_TO_S,	"adr",		32),
			(M_TO_S,	"select",	1),
			(M_TO_S,	"rnw",		1),
			(M_TO_S,	"seq_adr",	1),
			
			(S_TO_M,	"xfer_ack",	1),
			(S_TO_M,	"err_ack",	1),
			(S_TO_M,	"retry",	1),
			
			(M_TO_S,	"be",		4),
			(M_TO_S,	"dat_w",	32),
			(S_TO_M,	"dat_r",	32)))

class Interconnect(SimpleInterconnect):
	pass

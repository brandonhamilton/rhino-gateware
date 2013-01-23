from migen.fhdl.structure import *

from library import opb

class CasperCore:
	aperture = 0x10000
	
	def __init__(self, module_name, base_addr, *extra_signals):
		self.module_name = module_name
		self.base_addr = base_addr
		self.extra_signals = extra_signals
		
		self.bus = opb.Interface()
	
	def get_fragment(self):
		module = Instance(self.module_name,
			Instance.Parameter("C_BASEADDR"
		
			Instance.ClockPort("OPB_Clk", domain="opb"),
			Instance.ResetPort("OPB_Rst", domain="opb"),
			Instance.Input("OPB_ABus", self.bus.adr),
			Instance.Input("OPB_select", self.bus.select),
			Instance.Input("OPB_RNW", self.bus.rnw),
			Instance.Input("OPB_seqAddr", self.bus.seq_adr),
			Instance.Output("Sl_xferAck" self.bus.xfer_ack),
			Instance.Output("Sl_errAck", self.bus.err_ack),
			Instance.Output("Sl_retry", self.bus.retry),
			Instance.Input("OPB_BE", self.bus.be),
			Instance.Input("OPB_DBus", self.bus.dat_w),
			Instance.Output("Sl_DBus", self.bus.dat_r),
			
			Instance.ClockPort("user_clk"),
			
			*extra_signals
		)
		return Fragment(instances=[module])

class SoftwareRegister(CasperCore):
	aperture = 4
	def __init__(self, base_addr, high_addr):
		self.data_out = Signal(32)
		CasperCore.__init__("opb_register_ppc2simulink", base_addr, high_addr,
			Instance.Output("user_data_out", self.data_out))

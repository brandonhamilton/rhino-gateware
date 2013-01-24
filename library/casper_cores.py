from migen.fhdl.structure import *

class CasperCore:
	def __init__(self, module_name, baseapp, aperture, *extra_signals):
		self.module_name = module_name
		self.bus, self.base_addr = baseapp.opb.request(aperture)
		self.aperture = aperture
		self.extra_signals = extra_signals
	
	def get_fragment(self):
		inst = Instance(self.module_name,
			Instance.Parameter("C_BASEADDR", self.base_addr),
			Instance.Parameter("C_HIGHADDR", self.base_addr + self.aperture - 1),
		
			Instance.ClockPort("OPB_Clk", domain="opb"),
			Instance.ResetPort("OPB_Rst", domain="opb"),
			Instance.Input("OPB_ABus", self.bus.adr),
			Instance.Input("OPB_select", self.bus.select),
			Instance.Input("OPB_RNW", self.bus.rnw),
			Instance.Input("OPB_seqAddr", self.bus.seq_adr),
			Instance.Output("Sl_xferAck", self.bus.xfer_ack),
			Instance.Output("Sl_errAck", self.bus.err_ack),
			Instance.Output("Sl_retry", self.bus.retry),
			Instance.Input("OPB_BE", self.bus.be),
			Instance.Input("OPB_DBus", self.bus.dat_w),
			Instance.Output("Sl_DBus", self.bus.dat_r),
			
			Instance.ClockPort("user_clk"),
			
			*self.extra_signals
		)
		return Fragment(instances=[inst])

class SoftwareRegister(CasperCore):
	def __init__(self, baseapp):
		self.data_out = Signal(32)
		CasperCore.__init__(self, "opb_register_ppc2simulink", baseapp, 4,
			Instance.Output("user_data_out", self.data_out))

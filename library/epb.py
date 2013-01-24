from migen.fhdl.structure import *

from library import opb

class EPB:
	def __init__(self, epb_pins):
		self._epb_pins = epb_pins
		self.opb = opb.Interface()
	
	def get_fragment(self):
		inst = Instance("epb_opb_bridge",
			Instance.Input("epb_cs_n", self._epb_pins.cs_n),
			Instance.Input("epb_oe_n", self._epb_pins.oe_n),
			Instance.Input("epb_r_w_n", self._epb_pins.r_w_n),
			Instance.Input("epb_be_n", self._epb_pins.be_n),
			Instance.Input("epb_addr", self._epb_pins.addr),
			Instance.Input("epb_addr_gp", self._epb_pins.addr_gp),
			Instance.Input("epb_data", self._epb_pins.data),
			Instance.Output("epb_rdy", self._epb_pins.rdy),

			Instance.ClockPort("OPB_Clk", domain="opb"),
			Instance.ResetPort("OPB_Rst", domain="opb"),
			Instance.Output("M_ABus", self.opb.adr),
			Instance.Output("M_select", self.opb.select),
			Instance.Output("M_RNW", self.opb.rnw),
			Instance.Output("M_seqAddr", self.opb.seq_adr),
			Instance.Input("OPB_xferAck", self.opb.xfer_ack),
			Instance.Input("OPB_errAck", self.opb.err_ack),
			Instance.Input("OPB_retry", self.opb.retry),
			Instance.Output("M_BE", self.opb.be),
			Instance.Output("M_DBus", self.opb.dat_w),
			Instance.Input("OPB_DBus", self.opb.dat_r)
		)
		return Fragment(instances=[inst])

from migen.fhdl.std import *
from migen.genlib.cdc import MultiReg, PulseSynchronizer
from migen.bus import wishbone

class GPMC(Module):
	def __init__(self, gpmc_pads, csr_cs_n_pad):
		self.wishbone = wishbone.Interface(16)
		
		###

		self.clock_domains.cd_gpmc = ClockDomain(reset_less=True)
		self.comb += self.cd_gpmc.clk.eq(gpmc_pads.clk)
		gpmc_d = TSTriple(16)
		self.specials += gpmc_d.get_tristate(gpmc_pads.d)

		# Register address
		gpmc_ar = Signal(26)
		self.sync.gpmc += If(~gpmc_pads.ale_n,
			gpmc_ar.eq(Cat(gpmc_d.i, gpmc_pads.a)))

		# Synchronize GPMC address and write data to sys domain
		gpmc_ar_sys = Signal(26)
		gpmc_dw_sys = Signal(16)
		self.specials += MultiReg(gpmc_ar, gpmc_ar_sys), MultiReg(gpmc_d.i, gpmc_dw_sys)

		# Synchronize read data to GPMC domain and drive GPMC data pins
		gpmc_dr_sys = Signal(16)
		self.specials += MultiReg(gpmc_dr_sys, gpmc_d.o, "gpmc")
		self.comb += gpmc_d.oe.eq(~csr_cs_n_pad & ~gpmc_pads.oe_n & gpmc_pads.ale_n)

		# Generate read/write pulses in sys domain
		pulse_read = PulseSynchronizer("gpmc", "sys")
		pulse_write = PulseSynchronizer("gpmc", "sys")
		self.submodules += pulse_read, pulse_write
		gpmc_active = Signal()
		gpmc_active_r = Signal()
		gpmc_start = Signal()
		self.comb += gpmc_active.eq(~csr_cs_n_pad & gpmc_pads.ale_n)
		self.sync.gpmc += gpmc_active_r.eq(gpmc_active), gpmc_start.eq(gpmc_active & ~gpmc_active_r)
		self.comb += [
			pulse_read.i.eq(gpmc_start & gpmc_pads.we_n),
			pulse_write.i.eq(gpmc_start & ~gpmc_pads.we_n)
		]

		# Access Wishbone
		self.sync += [
			If(~self.wishbone.cyc & (pulse_read.o | pulse_write.o),
				self.wishbone.cyc.eq(1),
				self.wishbone.stb.eq(1),
				self.wishbone.we.eq(pulse_write.o),
				self.wishbone.adr.eq(gpmc_ar_sys),
				self.wishbone.dat_w.eq(gpmc_dw_sys)
			),
			If(self.wishbone.ack,
				self.wishbone.cyc.eq(0),
				self.wishbone.stb.eq(0),
				gpmc_dr_sys.eq(self.wishbone.dat_r)
			)
		]
		self.comb += self.wishbone.sel.eq(0b11),

		# Generate GPMC wait signal
		pulse_done = PulseSynchronizer("sys", "gpmc")
		self.submodules += pulse_done
		self.comb += pulse_done.i.eq(self.wishbone.ack)
		self.sync.gpmc += \
			If(~gpmc_pads.ale_n,
				gpmc_pads.wait.eq(1)
			).Elif(pulse_done.o,
				gpmc_pads.wait.eq(0)
			)

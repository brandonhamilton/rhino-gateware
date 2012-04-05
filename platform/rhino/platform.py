from migen.fhdl.structure import *
from migen.fhdl import verilog

from tools.cmgr import *
from library.gpmc import *

TARGET_VENDOR = "xilinx"
TARGET_DEVICE = "xc6slx150t-fgg676-3"

PLATFORM_RESOURCES = [
    ("user_led", 0, Pins("Y3")),
    ("user_led", 1, Pins("Y1")),
    ("user_led", 2, Pins("W2")),
    ("user_led", 3, Pins("W1")),
    ("user_led", 4, Pins("V3")),
    ("user_led", 5, Pins("V1")),
    ("user_led", 6, Pins("U2")),
    ("user_led", 7, Pins("U1")),
    
    ("sys_clk_p", 0, Pins("B14"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
    ("sys_clk_n", 0, Pins("A14"), IOStandard("LVDS_25"), Misc("DIFF_TERM=TRUE")),
    
    ("gpio", 0, Pins("R8")),
    
    ("gpmc", 0, 
        Subsignal("clk", Pins("R26")),
        Subsignal("a", Pins("N17", "N18", "L23", "L24", "N19", "N20", "N21", "N22", "P17", "P19")),
        Subsignal("d", Pins("N23", "N24", "R18", "R19", "P21", "P22", "R20", "R21", "P24", "P26", "R23", "R24", "T22", "T23", "U23", "R25")),
        Subsignal("we_n", Pins("W26")),
        Subsignal("oe_n", Pins("AA25")),
        Subsignal("ale_n", Pins("AA26")),
        IOStandard("LVCMOS33")),
    ("gpmc_wait", 0, Pins("AD26"), IOStandard("LVCMOS33")),
    ("gpmc_wait", 1, Pins("AB24"), IOStandard("LVCMOS33")),
    # Warning: CS are numbered 1-7 on ARM side and 0-6 on FPGA side.
    # Numbers here are given on the FPGA side.
    ("gpmc_ce_n", 0, Pins("V23"), IOStandard("LVCMOS33")), # nCS0
    ("gpmc_ce_n", 1, Pins("U25"), IOStandard("LVCMOS33")), # nCS1
    ("gpmc_ce_n", 2, Pins("W25"), IOStandard("LVCMOS33")), # nCS6
    ("gpmc_dmareq_n", 0, Pins("T24"), IOStandard("LVCMOS33")), # nCS2
    ("gpmc_dmareq_n", 1, Pins("T26"), IOStandard("LVCMOS33")), # nCS3
    ("gpmc_dmareq_n", 2, Pins("V24"), IOStandard("LVCMOS33")), # nCS4
    ("gpmc_dmareq_n", 3, Pins("V26"), IOStandard("LVCMOS33")), # nCS5
]

class CRG:
    def __init__(self, cm):
        self.sys_clk = Signal()
        self.sys_rst = cm.request("gpio", 0)
        self._inst = Instance("IBUFGDS",
            [("O", self.sys_clk)],
            [("I", cm.request("sys_clk_p")), ("IB", cm.request("sys_clk_n"))]
        )

    def get_fragment(self):
        return Fragment(instances=[self._inst])

class BaseApp:
    def __init__(self, cm, components):
        self.cm = cm
        
        self.streams_from = []
        self.streams_to = []
        
        self.crg = CRG(cm)
    
    def get_fragment(self):
        s_count = len(self.streams_from) + len(self.streams_to)
        dmareq_pins = [self.cm.request("gpmc_dmareq_n", i) for i in range(s_count)]
        gpmc_bridge = GPMC(self.cm.request("gpmc"),
            self.cm.request("gpmc_wait", 0),
            self.cm.request("gpmc_ce_n", 0), self.cm.request("gpmc_ce_n", 1),
            dmareq_pins, self.streams_from, self.streams_to)
        return self.crg.get_fragment() + gpmc_bridge.get_fragment() 
    
    def get_formatted_symtab(self):
        return ""
    
    def get_source(self):
        f = self.get_fragment()
        symtab = self.get_formatted_symtab()
        vsrc, ns = verilog.convert(f,
            self.cm.get_io_signals(),
            clk_signal=self.crg.sys_clk, rst_signal=self.crg.sys_rst,
            return_ns=True)
        return vsrc, ns, symtab

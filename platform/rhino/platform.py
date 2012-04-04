from migen.fhdl.structure import *
from migen.fhdl import verilog

from tools.cmgr import *

TARGET_VENDOR = "xilinx"
TARGET_DEVICE = "xc6slx150t-fgg676-3"

# TODO: complete me!
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
    
    #("gpmc", 0, 
        #Subsignal("CE0", Pins("A23")),
        #Subsignal("A", Pins("C23", "C32", "I23")),
    #IOStandard("LVCMOS33"))
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
        self.crg = CRG(cm)
    
    def get_fragment(self):
        return self.crg.get_fragment()
    
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

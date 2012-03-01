#     _____                 
#    (, /   ) /)   ,        
#      /__ / (/     __   ___
#   ) /   \_ / )__(_/ (_(_)   Tools
#  (_/                      
#       Reconfigurable Hardware Interface
#          for computatioN and radiO
#          
#  ========================================
#        http://www.rhinoplatform.org
#  ========================================
#
#   Rhino platform generator
#   Copyright (C) 2012 Brandon Hamilton
#
#   This file is part of rhino-tools.
#
#   rhino-tools is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   rhino-tools is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with rhino-tools.  If not, see <http://www.gnu.org/licenses/>.

from migen.fhdl.structure import *
from migen.fhdl import verilog, autofragment

from rhino import led, gpmc, clkgen

# If True, Prints out generated verilog code, constraints and BOF header file
DEBUG = True

# Create the User Constraints file for the platform
def _createConstraints(ns,clkgen,leds,sys_reset):
    constraints = []

    # Helper methods
    def add(signal, pin, vec=-1, iostandard="LVCMOS33", extra=""):
        constraints.append((ns.get_name(signal), vec, pin, iostandard, extra))
    
    def add_vec(signal, pins, iostandard="LVCMOS33", extra=""):
        assert(signal.bv.width == len(pins))
        i = 0
        for p in pins:
            add(signal, p, i, iostandard, extra)
            i += 1

    # Generate constraints for components
    add_vec(leds.led_register, ["Y3","Y1","W2","W1","V3","V1","U2","U1"])
    add(clkgen.sys_clk_p_i,"B14",iostandard="LVDS_25",extra="DIFF_TERM=TRUE")
    add(clkgen.sys_clk_n_i,"A14",iostandard="LVDS_25",extra="DIFF_TERM=TRUE")
    add(sys_reset,"R8",extra="SLEW=SLOW")
    
    # Convert to UCF
    c = ""
    for constraint in constraints:
        c += "NET \"" + constraint[0]
        if constraint[1] >= 0:
            c += "(" + str(constraint[1]) + ")"
        c += "\" LOC = " + constraint[2] 
        c += " | IOSTANDARD = " + constraint[3]
        if constraint[4]:
            c += " | " + constraint[4]
        c += ";\n"

    # Add timing constraints
    c += """
TIMESPEC "TS_sys_clk" = PERIOD "TM_sys_clk"  10.0  ns HIGH 50 %;
"""    
    return c

# Create the symbol table file for BORPH
def _createRegisterDefinitions():
    return """"""

# Generate platform HDL source code
# Returns a tuple: (verilog_source, platform_constraints, register_definitions)
def generate():

    # Create the system reset signal
    sys_reset = Signal(name="sys_rst")

    # === Build the platform here === #

    clkgen_obj = clkgen.CLKGEN()

    led_obj = led.LED()

    # =============================== #

    # Generate fragments from platform components
    frag = autofragment.from_local()
    # Generate HDL code
    verilog_source, verilog_namespace = verilog.convert(frag, { sys_reset }, name="rhino", rst_signal=sys_reset, clk_signal=clkgen_obj.sys_clk, return_ns=True)
    # Generate platform constraints
    platform_constraints = _createConstraints(verilog_namespace,clkgen_obj,led_obj,sys_reset)
	
    # Generate register definitions
    register_definitions = _createRegisterDefinitions()

    if DEBUG:
        print("----[Verilog]------------\r\n")
        print(verilog_source)
        print("----[Constraints]--------\r\n")
        print(platform_constraints)
        print("----[Registers]----------\r\n")
        print(register_definitions)
        print("-------------------\r\n")

    return (verilog_source, platform_constraints, register_definitions)

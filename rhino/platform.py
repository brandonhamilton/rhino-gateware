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
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   Foobar is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with rhino-tools.  If not, see <http://www.gnu.org/licenses/>.

from migen.fhdl.structure import *
from migen.fhdl import verilog, autofragment

from rhino import led, gpmc, clkgen

DEBUG = True

# Create the User Constraints file for the platform
def _createConstraints(ns,leds,clkgen):
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
    add(clkgen.sys_clk_p_i,"D3")
    add(clkgen.sys_clk_n_i,"D4")
    

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
    # Create system clock
    sys_clk = Signal(name="sys_clk")
    #no_sys_clk = Signal()
    sys_reset = Signal(name="sys_rst")

    # === Build the platform here ===
    led_obj = led.LED()
    #gpmc_obj = gpmc.GPMC(sys_clk)
    clkgen_obj = clkgen.CLKGEN()

    frag = autofragment.from_local()
        
    # Generate HDL code
    verilog_source, verilog_namespace = verilog.convert(frag, { sys_clk,sys_reset }, name="rhino", rst_signal=sys_reset,clk_signal=sys_clk,return_ns=True)
    # Generate platform constraints
    #platform_constraints = _createConstraints(verilog_namespace, gpmc_obj,led_obj)
    platform_constraints = _createConstraints(verilog_namespace,led_obj,clkgen_obj)
	
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

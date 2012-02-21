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

from rhino import led, gpmc

DEBUG = True

# Create the User Constraints file for the platform
def _createConstraints(gpmc, leds):
    c = ""

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
    sys_reset = Signal(name="sys_rst")

    # === Build the platform here ===
    led_obj = led.LED(sys_clk)
    gpmc_obj = gpmc.GPMC(sys_clk)

    frag = autofragment.from_local()
        
    # Generate HDL code
    verilog_source = verilog.convert(frag, { sys_clk, sys_reset }, name="rhino", clk_signal=sys_clk, rst_signal=sys_reset)
    # Generate platform constraints
    platform_constraints = _createConstraints(led_obj, gpmc_obj)
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
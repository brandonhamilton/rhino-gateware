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
#   Rhino application generator
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

from library import clkgen
import led

#--------------------------------------------------------------------------------#
# Generate application HDL source code                                           #
# Returns a tuple: (verilog_source, verilog_namespace, symbol_table, io)         #
#--------------------------------------------------------------------------------#
def get_application(app_name):

    # =============================== #
    # >>> Build the platform here     #
    # =============================== #

    # Create the system reset signal
    sys_reset = Signal(name="sys_rst")
    # Create the system clock generator
    clkgen_obj = clkgen.CLKGEN()

    # Create the led flasher
    led_obj = led.LEDFlash()

    # =============================== #
    # Generate the register defitions
    register_defitions = ""
    # Generate fragments from platform components
    frag = autofragment.from_local()

    # Generate HDL code
    verilog_source, verilog_namespace = verilog.convert(frag, { sys_reset }, name=app_name, rst_signal=sys_reset, clk_signal=clkgen_obj.sys_clk, return_ns=True)
    return (verilog_source, verilog_namespace, register_defitions, set())

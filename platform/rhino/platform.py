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

#-----------------------------------------------------------------------------#
# Platform settings                                                           #
#-----------------------------------------------------------------------------#
TARGET_VENDOR = "xilinx"
TARGET_DEVICE = "xc6slx75t-fgg676-3"

#-----------------------------------------------------------------------------#
# Libary component constraints for this platform                              #
#-----------------------------------------------------------------------------#
PLATFORM_CONSTRAINTS = {
  'led_register': {'pins': ["Y3","Y1","W2","W1","V3","V1","U2","U1"]},
  'sys_clk_p_i' : {'pins': ["B14"], 'iostandard':"LVDS_25", 'extra': "DIFF_TERM=TRUE" },
  'sys_clk_n_i' : {'pins': ["A14"], 'iostandard':"LVDS_25", 'extra': "DIFF_TERM=TRUE" },
  'sys_reset'   : {'pins': ["R8"], 'extra': "SLEW=SLOW" },
}

#-----------------------------------------------------------------------------#
# Helper functions and classes                                                #
#-----------------------------------------------------------------------------#
def _create_constraints(ns, signals, additional=None):
    constraints = []
    
    for signal in signals:
        signal_name = ns.get_name(signal)
        if signal_name in PLATFORM_CONSTRAINTS:
            signal_properties = PLATFORM_CONSTRAINTS[signal_name]
            number_of_pins = len(signal_properties['pins'])
            if number_of_pins < 1: continue

            iostandard = 'iostandard' in signal_properties and signal_properties['iostandard'] or 'LVCMOS33'
            extra = 'extra' in signal_properties and signal_properties['extra'] or ""

            if number_of_pins > 1:
                assert(signal.bv.width == number_of_pins)
                i = 0
                for p in signal_properties['pins']:
                    constraints.append((signal_name, i, p, iostandard, extra))
                    i += 1
            else:
                constraints.append((signal_name, -1, signal_properties['pins'][0], iostandard, extra))

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
    if additional: c += additional

    return c

#-----------------------------------------------------------------------------#
# Generate platform HDL source code                                           #
# Returns platform constraints as a string                                    #
#-----------------------------------------------------------------------------#
def get_platform(namespace, signals=None):

    # Set the platform timing constraints
    ts = """TIMESPEC "TS_sys_clk" = PERIOD "TM_sys_clk"  10.0  ns HIGH 50 %;"""

    # Generate platform constraints
    platform_constraints = _create_constraints(namespace, signals, ts)
    return platform_constraints

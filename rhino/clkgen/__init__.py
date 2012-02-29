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
#   Rhino platform - clkgen core
#   Copyright (C) 2012 Brandon Hamilton
#   Copyrigth (C) 2012 Alan Langman
#:
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
from migen.bank import description
import math

class CLKGEN:
    COUNT = 8

    def __init__(self,clk_freq=100e6):
        self.clk_freq   = clk_freq;
        self.sys_clk_n = Signal
        self.led_sync = [
                        ] 
   
    def get_fragment(self):

        # Return fragment with combinatoral and synchronous lists here
        return Fragment(sync=self.led_sync, pads={self.led_register})

       

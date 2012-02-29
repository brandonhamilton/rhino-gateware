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
#   Rhino platform - LED core
#   Copyright (C) 2012 Brandon Hamilton
#   Copyrigth (C) 2012 Alan Langman
#:
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
from migen.bank import description
import math

class LED:
    COUNT = 8

    def __init__(self,clk_freq=100e6,sweep_freq=2):
        self.CLK_DIVIDE_COUNT   = int(clk_freq/sweep_freq);
        self.CLK_DIVIDE_COUNT_N = int(math.ceil(math.log(self.CLK_DIVIDE_COUNT,2)))
        self.led_register = Signal(BV(LED.COUNT), reset = 0b10101010)
        self.clk_count = Signal(BV(self.CLK_DIVIDE_COUNT_N), reset = self.CLK_DIVIDE_COUNT)
        self.led_sync = [
                           If(self.clk_count == Constant(0,BV(self. CLK_DIVIDE_COUNT_N)),
                              self.clk_count.eq(self.CLK_DIVIDE_COUNT),
                              self.led_register.eq((self.led_register >> 1) | (self.led_register << 1 & 0b1000000))
                             ).Else(
                              self.clk_count.eq(self.clk_count-1)
                                   )
                        ] 
   
    def get_fragment(self):

        # Return fragment with combinatoral and synchronous lists here
        return Fragment(sync=self.led_sync, pads={self.led_register})

       

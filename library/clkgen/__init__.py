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
#   Copyright (C) 2012 Alan Langman
#   Copyrigth (C) 2012 Brandon Hamilton
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
from migen.fhdl import verilog

class CLKGEN:
    def __init__(self):
        self.sys_clk = Signal()
        self.sys_clk_n_i = Signal()
        self.sys_clk_p_i = Signal()
        self.inst = Instance("IBUFGDS",
                            [("O",self.sys_clk)],
                            [("I",self.sys_clk_p_i),("IB",self.sys_clk_n_i)],
                            parameters = [
                                    ("DIFF_TERM","FALSE"),
                                    ("IOSTANDARD","DEFAULT"),
                                    ("IBUF_DELAY_VALUE","0")], 
                            clkport=None,
                            rstport="",
                            name="IBUFGDS_inst")

    def get_fragment(self):
        return Fragment(instances=[self.inst])

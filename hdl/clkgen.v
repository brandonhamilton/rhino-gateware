//     _____                  
//    (, /   ) /)   ,         
//      /__ / (/     __   ___ 
//   ) /   \_ / )__(_/ (_(_)   Tools 
//  (_/                       
//       Reconfigurable Hardware Interface 
//          for computatioN and radiO 
//           
//  ======================================== 
//        http://www.rhinoplatform.org 
//  ========================================
//
//   Rhino platform hdl: clkgen.v
//   Copyright (C) 2012 Alan Langman
//
//   This file is part of rhino-tools.
//
//   rhino-tools is free software: you can redistribute it and/or modify
//   it under the terms of the GNU General Public License as published by
//   the Free Software Foundation, either version 2 of the License, or
//   (at your option) any later version.
//
//   Foobar is distributed in the hope that it will be useful,
//   but WITHOUT ANY WARRANTY; without even the implied warranty of
//   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//   GNU General Public License for more details.
//
//   You should have received a copy of the GNU General Public License
//   along with rhino-tools.  If not, see <http://www.gnu.org/licenses/>.


module clkgen 
(
    input sys_clk_n,
    input sys_clk_p,
    output sys_clk
);

IBUFGDS #(
   .DIFF_TERM("FALSE"),
   .IOSTANDARD("DEFAULT"),
   .IBUF_DELAY_VALUE("0")
                           //   the buffer: "0"-"12" (Spartan-3E)
) IBUFGDS_inst (
   .O(sys_clk),    // Clock buffer output
   .I(sys_clk_p),  // Diff_p clock buffer input
   .IB(sys_clk_n)  // Diff_n clock buffer input
);
// End of IBUFGDS_i`nst instantiation

endmodule


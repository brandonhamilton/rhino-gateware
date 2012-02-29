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
#   Rhino platform build file
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

import os
import rhino.platform

#-----------------------------------------------------------------------------#
# Helper functions and classes                                                #
#-----------------------------------------------------------------------------#

# Save a string to a file
def writeToFile(filename, contents):
    f = open(filename, "w")
    f.write(contents)
    f.close()

# Find all HDL source files within a path
def findHDLSourceFiles(path="."):
    sources = []
    for root, dirs, files in os.walk(path):
        for name in files:
            try:
                extension = name.rsplit('.')[-1]
                if extension in ["vhd", "vhdl", "vho"]:
                    sources.extend({"type": "vhdl", "path": os.path.join(root, name)})
                elif extension in ["v", "vh", "vo"]:
                    sources.extend({"type": "verilog", "path": os.path.join(root, name)})
            except:
                pass
    return sources

# Xilinx FPGA-based build toolflow
class XilinxBuilder:
    def __init__(self, sources, *, name="rhino", ucf="rhino.ucf", top=None):
        self.build_name = name
        self.ucf_file = ucf
        self.top_module = top and top or name
        # Generate project file
        prjContents = ""
        for s in sources:
            prjContents += "%s %s ../%s\n" % (s["type"], s["library"] if "library" in s else "work", s["path"])
        writeToFile("%s.prj" % (self.build_name), prjContents)
        # Generate XST script
        xstContents = """run
-ifn %s.prj
-top %s
-ifmt MIXED
-opt_mode SPEED
-reduce_control_sets auto
-ofn %s.ngc
-p xc6slx150t-fgg676-3""" % (self.build_name, self.top_module, self.build_name)
        writeToFile("%s.xst" % (self.build_name), xstContents)

    def _buildNetlist(self):
        os.system("xst -ifn %s.xst" % (self.build_name))

    def _buildNativeGenericDatabase(self):
        os.system("ngdbuild -uc %s %s.ngc" % (self.ucf_file, self.build_name))

    def _buildNativeCircuitDescription(self):
        os.system("map -ol high -w %s.ngd" % (self.build_name))

    def _performPlaceAndRoute(self):
        os.system("par -ol high -w %s.ncd %s-routed.ncd" % (self.build_name, self.build_name))

    def _buildBitstream(self):
        os.system("bitgen -g Binary:Yes -w %s-routed.ncd %s.bit" % (self.build_name, self.build_name))

    def _buildBOF(self):
        os.system("mkbof -t 5 -s %s.symtab -o %s.bof %s.bin" % (self.build_name,self.build_name, self.build_name))

    def build(self):
        # XST
        self._buildNetlist()
        # NGD
        self._buildNativeGenericDatabase()
        # Mapping
        self._buildNativeCircuitDescription()
        # Place and Route
        self._performPlaceAndRoute()
        # Generate FPGA configuration
        self._buildBitstream()
        # BORPH Object file (BOF) generation
        self._buildBOF()

#-----------------------------------------------------------------------------#
# Perform Build steps                                                         #
#-----------------------------------------------------------------------------#

build_name = "rhino"

# 1. Find all HDL source files
sources = findHDLSourceFiles("hdl")

# 2. Setup build dir
os.system("rm -rf build/*")
os.chdir("build")

# 3. Generate additional sources with migen
(generated_hdl_src, ucf_src, symtab_src) = rhino.platform.generate()

generated_hdl_file = "%s.v" % (build_name)
writeToFile(generated_hdl_file, generated_hdl_src)
sources.extend([{"type":"verilog", "path":"build/%s.v" % (build_name), "library":"%s" % (build_name)}])

# 4. Create User Constraints file
ucf_file = "%s.ucf" % (build_name)
writeToFile(ucf_file, ucf_src)

# 5. Create BORPH symbol table
symtab_file = "%s.symtab" % (build_name)
writeToFile(symtab_file, symtab_src)

# 5. Synthesize project
builder = XilinxBuilder(sources, ucf=ucf_file)
builder.build()

#!/usr/bin/env python3
#
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

import os, sys
import imp, inspect
sys.path.append(os.getcwd())

#-----------------------------------------------------------------------------#
# Build Settings                                                              #
#-----------------------------------------------------------------------------#
platform = "rhino"  # Build platform
DEBUG    = False    # Print generated code to stdout

#-----------------------------------------------------------------------------#
# Helper functions and classes                                                #
#-----------------------------------------------------------------------------#

# Save a string to a file
def write_to_file(filename, contents):
    f = open(filename, "w")
    f.write(contents)
    f.close()

# Ensure a directory exists
def ensure_dirs(d):
    for f in d:
        if not os.path.exists(f):
            os.makedirs(f)

# Find all HDL source files within a path
def find_hdl_source_files(path="."):
    sources = []
    for root, dirs, files in os.walk(path):
        for name in files:
            try:
                extension = name.rsplit('.')[-1]      
                if extension in ["vhd", "vhdl", "vho"]:
                    sources.extend([{"type": "vhdl", "path": os.path.join(root, name)}])
                elif extension in ["v", "vh", "vo"]:
                    sources.extend([{"type": "verilog", "path": os.path.join(root, name)}])
            except:
                pass
    return sources

# Return a list of migen components
def get_components():
    f = []
    frame = inspect.currentframe().f_back
    ns = frame.f_locals
    for x in ns:
        obj = ns[x]
        if hasattr(obj, "get_fragment"):
            f.append(obj)
    return f

# Xilinx FPGA-based build toolflow
class XilinxBuilder:
    def __init__(self, sources, *, name="rhino", ucf=None, top=None):
        self.build_name = name
        self.ucf_file = ucf and ucf or "%s.ucf" % (name)
        self.top_module = top and top or name
        # Generate project file
        prjContents = ""
        for s in sources:
            prjContents += "%s %s ../../../%s\n" % (s["type"], s["library"] if "library" in s else "work", s["path"])
        write_to_file("%s.prj" % (self.build_name), prjContents)
        # Generate XST script
        xstContents = """run
-ifn %s.prj
-top %s
-ifmt MIXED
-opt_mode SPEED
-reduce_control_sets auto
-ofn %s.ngc
-p xc6slx150t-fgg676-3""" % (self.build_name, self.top_module, self.build_name)
        write_to_file("%s.xst" % (self.build_name), xstContents)

    def _build_netlist(self):
        os.system("xst -ifn %s.xst" % (self.build_name))

    def _build_native_generic_database(self):
        os.system("ngdbuild -uc %s %s.ngc" % (self.ucf_file, self.build_name))

    def _build_native_circuit_description(self):
        os.system("map -ol high -w %s.ngd" % (self.build_name))

    def _perform_place_and_route(self):
        os.system("par -ol high -w %s.ncd %s-routed.ncd" % (self.build_name, self.build_name))

    def _build_bitstream(self):
        os.system("bitgen -g Binary:Yes -w %s-routed.ncd %s.bit" % (self.build_name, self.build_name))

    def _build_borph_object_file(self):
        os.system("mkbof -t 5 -s %s.symtab -o %s.bof %s.bin" % (self.build_name,self.build_name, self.build_name))

    def build(self):
        # XST
        self._build_netlist()
        # NGD
        self._build_native_generic_database()
        # Mapping
        self._build_native_circuit_description()
        # Place and Route
        self._perform_place_and_route()
        # Generate FPGA configuration
        self._build_bitstream()
        # BORPH Object file (BOF) generation
        self._build_borph_object_file()

def print_header():
    print('     _____                               ')
    print('    (, /   ) /)   ,                      ')
    print('      /__ / (/     __   ___              ')
    print('   ) /   \_ / )__(_/ (_(_)   Tools       ')
    print('  (_/                                    ')
    print('       Reconfigurable Hardware Interface ')
    print('          for computatioN and radiO      \r\n')
    print(' ========================================')
    print('        http://www.rhinoplatform.org')
    print(' ========================================\r\n')

#-----------------------------------------------------------------------------#
# Perform Build steps                                                         #
#-----------------------------------------------------------------------------#

if __name__ == "__main__":

    print_header()

    # Load platform
    platform_module = imp.load_source('%s' % (platform), 'platform/%s/platform.py' % (platform))

    # Select applications to build
    apps = [f for f in os.listdir("application") if os.path.isdir("application/%s" % f)]

    if len(sys.argv) > 1:
        apps = list(set(sys.argv[1:]) & set(apps))

    if 'template' in apps: apps.remove('template')

    # Find all HDL source files
    source_hdl = find_hdl_source_files("library/hdl")

    # Build each application
    for build_name in apps:
        print(" Building '%s'..." % build_name)
        changed_dir = False
        try:
            # 1. Import the application
            application_module = imp.load_source('%s' % build_name, 'application/%s/top.py' % (build_name))

            # 2. Setup build dir
            os.chdir("application/%s" % build_name)
            changed_dir = True
            ensure_dirs(['build', 'output'])
            os.system("rm -rf output/*")
            os.system("rm -rf build/*")
            os.chdir("build")
            
            # 4. Generate additional sources with migen
            (generated_hdl_src, namespace, symtab_src, signals) = application_module.get_application(build_name)
            if DEBUG:
                print("----[Verilog]------------")
                print(generated_hdl_src)
            generated_hdl_file = "%s.v" % (build_name)
            write_to_file(generated_hdl_file, generated_hdl_src)
            app_source_hdl = [{"type":"verilog", "path":"build/%s.v" % (build_name), "library":"%s" % (build_name)}]
            app_source_hdl.extend(source_hdl)

            write_to_file("%s.symtab" % (build_name), symtab_src)
            if DEBUG:
                print("----[Registers]----------")
                print(symtab_src)

            # 5. Generate platform code
            ucf_src = platform_module.get_platform(namespace, signals)
            write_to_file("%s.ucf" % (build_name), ucf_src)
            if DEBUG:
                print("----[Constraints]--------")
                print(ucf_src)
                print("-------------------------\r\n")

            # 5. Synthesize project
            builder = XilinxBuilder(app_source_hdl, name=build_name)
            builder.build()

            # 6. Move BOF file
            if os.path.exists('%s.bof' % (build_name)):
                os.system("mv %s.bof ../output/" % (build_name))

            print(" Completed build of '%s'" % build_name)
        except Exception as e:
            print(" Build Error: %s" % (e));

        if changed_dir: os.chdir("../../../")

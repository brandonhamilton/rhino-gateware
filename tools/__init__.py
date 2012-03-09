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
#   Build tool helper functions
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

import os, inspect

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
def find_hdl_source_files(path=".", library="work", path_prefix=""):
    sources = []
    for root, dirs, files in os.walk(path):
        for name in files:
            try:
                extension = name.rsplit('.')[-1]      
                if extension in ["vhd", "vhdl", "vho"]:
                    sources.extend([{"type": "vhdl", "path": "%s%s" %  (path_prefix, os.path.join(root, name)), "library":library}])
                elif extension in ["v", "vh", "vo"]:
                    sources.extend([{"type": "verilog", "path": "%s%s" % (path_prefix, os.path.join(root, name)), "library":library}])
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

# Create BOF file
def generate_bof(build_name, symbol_table=None, bin_file=None):
    symtab = symbol_table and symbol_table or "%s.symtab" % (build_name)
    bin = bin_file and bin_file or "%s.bin" % (build_name)
    os.system("mkbof -t 5 -s %s -o %s.bof %s" % (symtab, build_name, bin))

# Write some nice art
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
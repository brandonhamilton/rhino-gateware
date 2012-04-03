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
#   Top Level Build file
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

import os, sys, imp, subprocess

import tools

#-----------------------------------------------------------------------------#
# Build Settings                                                              #
#-----------------------------------------------------------------------------#
platform = "rhino"  # Build platform
DEBUG    = True     # Print generated code to stdout

#-----------------------------------------------------------------------------#
# Perform Build steps                                                         #
#-----------------------------------------------------------------------------#

if __name__ == "__main__":
    tools.print_header()
    
    orig_dir = os.getcwd()

    # Load platform
    platform_module = imp.load_source(platform, os.path.join("platform", platform, "platform.py"))
    builder_module = imp.load_source(platform_module.TARGET_VENDOR, os.path.join("tools", platform_module.TARGET_VENDOR + ".py"))

    # Select applications to build
    if len(sys.argv) > 1:
        apps = list(set(sys.argv[1:]) & set(apps))
    else:
        apps = [f for f in os.listdir("application") if os.path.isdir(os.path.join("application", f))]

    # Find all library HDL source files
    library_hdl = tools.find_hdl_source_files(os.path.join(orig_dir, "library", "hdl"))

    # Build each application
    for build_name in apps:
        print(" Building '%s'..." % build_name)
        
        # Prepare environment
        application_dir = os.path.join(orig_dir, "application", build_name)
        build_dir = os.path.join(application_dir, "build")
        output_dir = os.path.join(application_dir, "output")
        tools.ensure_empty_dir(build_dir)
        tools.ensure_empty_dir(output_dir)
        sys.path.insert(0, application_dir)
        
        # Import the required modules
        application_module = imp.load_source(build_name, os.path.join(application_dir, "top.py"))
        
        # Generate sources with Migen
        (generated_hdl_src, namespace, symtab_src, signals) = application_module.get_application(build_name)
        if DEBUG:
            print("----[Verilog]------------")
            print(generated_hdl_src)
        generated_hdl_file = os.path.join(build_dir, build_name + ".v")
        tools.write_to_file(generated_hdl_file, generated_hdl_src)
        application_hdl = [{"type":"verilog", "path":os.path.join(application_dir, "build", generated_hdl_file)}]

        tools.write_to_file(os.path.join(build_dir, build_name + ".symtab"), symtab_src)
        if DEBUG:
            print("----[Registers]----------")
            print(symtab_src)

        # Generate platform code
        ucf_src = platform_module.get_platform(namespace, signals)
        tools.write_to_file(os.path.join(build_dir, build_name + ".ucf"), ucf_src)
        if DEBUG:
            print("----[Constraints]--------")
            print(ucf_src)
            print("-------------------------\r\n")

        # Include library and application HDL files
        application_hdl += tools.find_hdl_source_files(os.path.join(application_dir, "hdl"))
        application_hdl += library_hdl
    
        # Synthesize project
        os.chdir(os.path.join(application_dir, "build"))
        bitstream = builder_module.build(platform_module.TARGET_DEVICE, application_hdl, build_name)
        os.chdir(orig_dir)

        # Create BOF file
        r = subprocess.call(["mkbof",
            "-t", "5",
            "-s", os.path.join(build_dir, build_name + ".symtab"),
            "-o", os.path.join(build_dir, build_name + ".bof"),
            os.path.join(build_dir, build_name + ".bin")])
        if r != 0:
            raise OSError("Subprocess failed")
        
        # Clean up environment
        sys.path.remove(application_dir)
        
        print(" Completed build of '%s'" % build_name)

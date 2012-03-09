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

import os, sys
import imp, inspect
sys.path.append(os.getcwd())

import tools

#-----------------------------------------------------------------------------#
# Build Settings                                                              #
#-----------------------------------------------------------------------------#
platform = "rhino"  # Build platform
DEBUG    = False    # Print generated code to stdout

#-----------------------------------------------------------------------------#
# Perform Build steps                                                         #
#-----------------------------------------------------------------------------#

if __name__ == "__main__":

    tools.print_header()

    # Load platform
    platform_module = imp.load_source('%s' % (platform), 'platform/%s/platform.py' % (platform))

    # Select applications to build
    apps = [f for f in os.listdir("application") if os.path.isdir("application/%s" % f)]

    if len(sys.argv) > 1:
        apps = list(set(sys.argv[1:]) & set(apps))

    if 'template' in apps: apps.remove('template')

    # Find all library HDL source files
    library_hdl = tools.find_hdl_source_files("library/hdl", "lib", "../../")

    # Build each application
    for build_name in apps:
        print(" Building '%s'..." % build_name)
        changed_dir = False
        application_path = "application/%s" % build_name
        sys.path.append(application_path)
        try:
            # 1. Import the required modules
            application_module = imp.load_source('%s' % build_name, '%s/top.py' % (application_path))
            builder_module = imp.load_source('%s' % platform_module.TARGET_VENDOR, 'tools/%s.py' % (platform_module.TARGET_VENDOR))
            os.chdir(application_path)

            # 2. Find all application HDL source files
            application_hdl = tools.find_hdl_source_files("hdl", build_name)

            # 3. Setup build dir
            tools.ensure_dirs(['build', 'output'])
            os.system("rm -rf output/*")
            os.system("rm -rf build/*")
            os.chdir("build")
            changed_dir = True
            
            # 4. Generate additional sources with migen
            (generated_hdl_src, namespace, symtab_src, signals) = application_module.get_application(build_name)
            if DEBUG:
                print("----[Verilog]------------")
                print(generated_hdl_src)
            generated_hdl_file = "%s.v" % (build_name)
            tools.write_to_file(generated_hdl_file, generated_hdl_src)
            application_include_hdl = [{"type":"verilog", "path":"build/%s.v" % (build_name), "library":"%s" % (build_name)}]

            # 5. Include Library and application HDL files
            application_include_hdl.extend(application_hdl)
            application_include_hdl.extend(library_hdl)

            tools.write_to_file("%s.symtab" % (build_name), symtab_src)
            if DEBUG:
                print("----[Registers]----------")
                print(symtab_src)

            # 6. Generate platform code
            ucf_src = platform_module.get_platform(namespace, signals)
            tools.write_to_file("%s.ucf" % (build_name), ucf_src)
            if DEBUG:
                print("----[Constraints]--------")
                print(ucf_src)
                print("-------------------------\r\n")

            # 6. Synthesize project
            bitstream = builder_module.build(platform_module.TARGET_DEVICE, application_include_hdl, build_name)

            # 7. Create BOF file
            tools.generate_bof(build_name)

            # 8. Move BOF file
            if os.path.exists('%s.bof' % (build_name)):
                os.system("mv %s.bof ../output/" % (build_name))

            print(" Completed build of '%s'" % build_name)
        except Exception as e:
            print(" Build Error: %s" % (e));

        sys.path.remove(application_path)
        if changed_dir: os.chdir("../../../")

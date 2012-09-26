#!/usr/bin/env python3

import os, sys, imp, subprocess

import tools

#-----------------------------------------------------------------------------#
# Build Settings                                                              #
#-----------------------------------------------------------------------------#
platform = "rhino"  # Build platform

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
		apps = sys.argv[1:]
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
		
		# Build application and generate sources
		app = platform_module.BaseApp(application_module.COMPONENTS)
		generated_hdl_src, namespace, sig_constraints, platform_commands, symtab_src = app.get_source()
		
		# Write sources to filesystem
		generated_hdl_file = os.path.join(build_dir, build_name + ".v")
		tools.write_to_file(generated_hdl_file, generated_hdl_src)
		tools.write_to_file(os.path.join(build_dir, build_name + ".symtab"), symtab_src)

		# Build list of HDL sources
		application_hdl = [{"type":"verilog", "path":os.path.join(application_dir, "build", generated_hdl_file)}]
		application_hdl += tools.find_hdl_source_files(os.path.join(application_dir, "hdl"))
		application_hdl += library_hdl
	
		# Synthesize project
		os.chdir(os.path.join(application_dir, "build"))
		bitstream = builder_module.build(platform_module.TARGET_DEVICE,
			application_hdl,
			namespace, sig_constraints, platform_commands,
			build_name)
		os.chdir(orig_dir)

		# Create BOF file
		r = subprocess.call(["mkbof",
			"-t", "5",
			"-s", os.path.join(build_dir, build_name + ".symtab"),
			"-o", os.path.join(output_dir, build_name + ".bof"),
			os.path.join(build_dir, build_name + ".bin")])
		if r != 0:
			raise OSError("Subprocess failed")
		
		# Clean up environment
		sys.path.remove(application_dir)
		
		print(" Completed build of '%s'" % build_name)

#!/usr/bin/env python3

import os, sys, imp, subprocess, argparse

import tools

def main():
	tools.print_header()
	
	parser = argparse.ArgumentParser(description="Build system and library for the RHINO platform and derivatives.")
	parser.add_argument("-e", "--extension-dir", action="append", default=[os.getcwd()])
	parser.add_argument("-p", "--platform", default="rhino")
	parser.add_argument("applications", nargs="+")
	args = parser.parse_args()
	search_dirs = list(map(os.path.abspath, reversed(args.extension_dir)))
	platform = args.platform
	apps = args.applications

	platform_module = tools.try_import(search_dirs, os.path.join("platform", platform), "platform")
	builder_module = tools.try_import(search_dirs, "tools", platform_module.TARGET_VENDOR)

	library_hdl = tools.find_hdl_source_files(os.path.join(search_dir, "library", "hdl") for search_dir in search_dirs)

	# Build each application
	for build_name in apps:
		print(" Building '%s'..." % build_name)
		
		# Prepare environment
		root_dir, application_dir = tools.find_dir(search_dirs, os.path.join("application", build_name))
		if application_dir is None:
			raise IOError("Could not find application " + build_name)
		build_dir = os.path.join(application_dir, "build")
		output_dir = os.path.join(application_dir, "output")
		tools.mkdir_noerror(build_dir)
		tools.mkdir_noerror(output_dir)
		sys.path.insert(0, root_dir)
		
		# Build application and generate sources
		application_module = imp.load_source(build_name, os.path.join(application_dir, "top.py"))
		app = platform_module.BaseApp(application_module.COMPONENTS)
		generated_hdl_src, namespace, sig_constraints, platform_commands, symtab_src = app.get_source()
		
		# Write sources to filesystem
		generated_hdl_file = os.path.join(build_dir, build_name + ".v")
		tools.write_to_file(generated_hdl_file, generated_hdl_src)
		tools.write_to_file(os.path.join(build_dir, build_name + ".symtab"), symtab_src)

		# Build list of HDL sources
		application_hdl = [{"type":"verilog", "path":os.path.join(application_dir, "build", generated_hdl_file)}]
		application_hdl += tools.find_hdl_source_files([os.path.join(application_dir, "hdl")])
		application_hdl += library_hdl
	
		# Synthesize project
		orig_dir = os.getcwd()
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
		sys.path.remove(root_dir)
		
		print(" Completed build of '%s'" % build_name)

if __name__ == "__main__":
	main()

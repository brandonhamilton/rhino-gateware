#!/usr/bin/env python3

import os, sys, imp, subprocess, argparse

def try_import(search_dirs, path, name):
	search_dirs = [os.path.join(search_dir, path) for search_dir in search_dirs]
	f, filename, data = imp.find_module(name, search_dirs)
	try:
		m = imp.load_module(name, f, filename, data)
	finally:
		f.close()
	return m

def find_dir(search_dirs, path):
	for search_dir in search_dirs:
		full_dir = os.path.join(search_dir, path)
		if os.path.isdir(full_dir):
			return search_dir, full_dir
	return None

def main():
	print("     _____                               ")
	print("    (, /   ) /)   ,                      ")
	print("      /__ / (/     __   ___              ")
	print("   ) /   \_ / )__(_/ (_(_)               ")
	print("  (_/                                    ")
	print("       Reconfigurable Hardware Interface ")
	print("          for computatioN and radiO")
	print("")
	print(" ========================================")
	print("        http://www.rhinoplatform.org")
	print(" ========================================")
	print("")
	
	parser = argparse.ArgumentParser(description="Build system and library for the RHINO platform and derivatives.")
	parser.add_argument("-e", "--extension-dir", action="append", default=[os.getcwd()])
	parser.add_argument("-p", "--platform", default="rhino")
	parser.add_argument("applications", nargs=1)
	args = parser.parse_args()
	search_dirs = list(map(os.path.abspath, reversed(args.extension_dir)))
	platform = args.platform
	app_name = args.applications[0]

	sys.path = search_dirs + sys.path
	platform_module = try_import(search_dirs, os.path.join("platform", platform), "platform")

	root_dir, application_dir = find_dir(search_dirs, os.path.join("application", app_name))
	if application_dir is None:
		raise IOError("Could not find application " + app_name)
	
	application_module = imp.load_source(app_name, os.path.join(application_dir, "app_toplevel.py"))
	toplevel = platform_module.Toplevel(application_module.AppToplevel)

	orig_dir = os.getcwd()
	os.chdir(application_dir)
	toplevel.build()
	os.chdir(orig_dir)

if __name__ == "__main__":
	main()

import os, subprocess, shutil, imp

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

# Save a string to a file
def write_to_file(filename, contents):
	f = open(filename, "w")
	f.write(contents)
	f.close()

# Find all HDL source files within paths
def find_hdl_source_files(paths):
	sources = []
	for path in paths:
		for root, dirs, files in os.walk(path):
			for name in files:
				try:
					extension = name.rsplit(".")[-1] 
					if extension in ["vhd", "vhdl", "vho"]:
						sources.extend([{"type": "vhdl", "path": os.path.join(root, name)}])
					elif extension in ["v", "vh", "vo"]:
						sources.extend([{"type": "verilog", "path": os.path.join(root, name)}])
				except:
					pass
	return sources

# Write some nice art
def print_header():
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

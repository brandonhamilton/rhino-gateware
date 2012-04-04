import os, subprocess, shutil

#-----------------------------------------------------------------------------#
# Helper functions and classes                                                #
#-----------------------------------------------------------------------------#

# Save a string to a file
def write_to_file(filename, contents):
    f = open(filename, "w")
    f.write(contents)
    f.close()

# Ensure a directory exists and is empty
def ensure_empty_dir(d):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)

# Find all HDL source files within a path
def find_hdl_source_files(path):
    sources = []
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
    print("   ) /   \_ / )__(_/ (_(_)   Tools       ")
    print("  (_/                                    ")
    print("       Reconfigurable Hardware Interface ")
    print("          for computatioN and radiO")
    print("")
    print(" ========================================")
    print("        http://www.rhinoplatform.org")
    print(" ========================================")
    print("")

from mibuild.platforms import rhino

from library.toplevel import GPMCToplevel

class Toplevel(GPMCToplevel):
	def __init__(self, app_toplevel_class):
		GPMCToplevel.__init__(self, 5, rhino.Platform(), app_toplevel_class)

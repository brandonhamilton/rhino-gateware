from mibuild.platforms import rhino

from library.baseapp import RhinoBaseApp
from library.crg import CRGFMC150

class BaseApp(RhinoBaseApp):
	def __init__(self, components):
		self.double_dac = True
		RhinoBaseApp.__init__(self, components, rhino.Platform(), 5,
			lambda app: CRGFMC150(app, double_dac=self.double_dac))

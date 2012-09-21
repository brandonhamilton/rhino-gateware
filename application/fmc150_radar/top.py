from library.crg import CRGFMC150
from library.led_controller import LedController
from library.fmc150_controller import FMC150Controller

COMPONENTS = [
	CRGFMC150,
	(LedController, {"count": 8}),
	FMC150Controller
]

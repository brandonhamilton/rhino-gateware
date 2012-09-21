from library.crg import CRGFMC150
from library.led_controller import LedBlinker, LedController
from library.fmc150_controller import FMC150Controller

COMPONENTS = [
	CRGFMC150,
	LedBlinker,
	(LedController, {"count": 4}),
	FMC150Controller
]

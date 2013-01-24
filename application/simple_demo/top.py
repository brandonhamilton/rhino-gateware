from library.baseapp import Comp

from library.led_controller import *
from library.demo_affine import *

COMPONENTS=[Comp(LedController, count=8), DemoAffine]

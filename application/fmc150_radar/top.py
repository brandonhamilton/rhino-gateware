from migen.flow.network import *
from migen.actorlib.structuring import Cast

from library.uid import UID_WAVEFORM_GENERATOR
from library.crg import CRGFMC150
from library.led_controller import LedBlinker, LedController
from library.fmc150_controller import FMC150Controller
from library.waveform_generator import WaveformGenerator
from library.fmc150_data import DAC2X

class FullWaveformGenerator(CompositeActor):
	def __init__(self, baseapp):
		dac_pins = baseapp.constraints.request("fmc150_dac")
		width = 2*len(dac_pins.dat_p)
		
		wg = ActorNode(WaveformGenerator(1024, 4*width))
		dac = ActorNode(DAC2X(dac_pins, baseapp.crg.dacio_strb))
		cast = ActorNode(Cast(wg.actor.token("sample").layout(),
			dac.actor.token("samples").layout()))
		
		registers = wg.actor.get_registers() + dac.actor.get_registers()
		baseapp.csrs.request("wg", UID_WAVEFORM_GENERATOR, *registers)
		
		g = DataFlowGraph()
		g.add_connection(wg, cast)
		g.add_connection(cast, dac)
		super().__init__(g)

COMPONENTS = [
	(CRGFMC150, {"double_dac": True}),
	LedBlinker,
	(LedController, {"count": 4}),
	FMC150Controller,
	FullWaveformGenerator
]

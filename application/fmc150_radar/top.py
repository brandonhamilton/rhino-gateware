from migen.flow.network import *
from migen.flow.plumbing import Buffer
from migen.actorlib.structuring import Cast
from migen.actorlib.spi import Collector

from library.uid import UID_WAVEFORM_GENERATOR, UID_WAVEFORM_COLLECTOR
from library.crg import CRGFMC150
from library.led_controller import LedBlinker, LedController
from library.fmc150_controller import FMC150Controller
from library.waveform_generator import WaveformGenerator
from library.fmc150_data import DAC, DAC2X, ADC

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

class FullWaveformCollector(CompositeActor):
	def __init__(self, baseapp):
		adc_pins = baseapp.constraints.request("fmc150_adc")
		width = 2*len(adc_pins.dat_a_p)
		
		adc = ActorNode(ADC(adc_pins))
		buf = ActorNode(Buffer)
		wc = ActorNode(Collector(adc.actor.token("samples").layout()))
		
		baseapp.csrs.request("wc", UID_WAVEFORM_COLLECTOR, *wc.actor.get_registers())
		
		g = DataFlowGraph()
		g.add_connection(adc, buf)
		g.add_connection(buf, wc)
		super().__init__(g)

COMPONENTS = [
	CRGFMC150,
	LedBlinker,
	(LedController, {"count": 4}),
	FMC150Controller,
	FullWaveformGenerator,
	FullWaveformCollector
]

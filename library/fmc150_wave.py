from migen.flow.network import *
from migen.flow.plumbing import Buffer
from migen.actorlib.spi import Collector
from migen.bank.description import regprefix

from library.uid import UID_WAVEFORM_GENERATOR, UID_WAVEFORM_COLLECTOR
from library.waveform_generator import WaveformGenerator
from library.fmc150_data import DAC, DAC2X, ADC

class FullWaveformGenerator(CompositeActor):
	def __init__(self, baseapp, double_dac):
		dac_pins = baseapp.constraints.request("fmc150_dac")
		width = 2*len(dac_pins.dat_p)
		
		spc = 2 if double_dac else 1
		dac_class = DAC2X if double_dac else DAC
		
		wg_i = WaveformGenerator(1024, width, spc)
		wg_q = WaveformGenerator(1024, width, spc)
		dac = dac_class(dac_pins, baseapp.crg.dacio_strb)

		registers = regprefix("i_", wg_i.get_registers()) \
			+ regprefix("q_", wg_q.get_registers()) \
			+ dac.get_registers()
		baseapp.csrs.request("wg", UID_WAVEFORM_GENERATOR, *registers)
		
		g = DataFlowGraph()
		if double_dac:
			g.add_connection(wg_i, dac, sink_subr=["i0", "i1"])
			g.add_connection(wg_q, dac, sink_subr=["q0", "q1"])
		else:
			g.add_connection(wg_i, dac, sink_subr=["i"])
			g.add_connection(wg_q, dac, sink_subr=["q"])
		super().__init__(g)

class FullWaveformCollector(CompositeActor):
	def __init__(self, baseapp):
		adc_pins = baseapp.constraints.request("fmc150_adc")
		width = 2*len(adc_pins.dat_a_p)
		
		adc = ADC(adc_pins)
		buf = AbstractActor(Buffer)
		wc = Collector(adc.token("samples").layout())
		
		baseapp.csrs.request("wc", UID_WAVEFORM_COLLECTOR, *wc.get_registers())
		
		g = DataFlowGraph()
		g.add_connection(adc, buf)
		g.add_connection(buf, wc)
		super().__init__(g)

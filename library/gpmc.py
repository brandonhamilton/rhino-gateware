from migen.fhdl.structure import *
from migen.bus import csr

class GPMC:
    def __init__(self, gpmc_pins, csr_cs_pin, dma_cs_pin, dmareq_pins, streams_from, streams_to):
        self._dmareq_pins = dmareq_pins
        self._streams_from = streams_from
        self._streams_to = streams_to
        
        s_from_count = len(self._streams_from)
        s_to_count = len(self._streams_to)
        s_count = s_from_count + s_to_count
        assert(len(dmareq_pins) == s_count)
        
        self.csr = csr.Interface()
        
        self._inst = Instance("gpmc",
            [
                ("csr_adr", self.csr.adr),
                ("csr_we", self.csr.we),
                ("csr_dat_w", self.csr.dat_w),
                
                ("s_from_stb", BV(s_from_count)),
                ("s_from_data", BV(16*s_from_count)),
                
                ("s_to_ack", BV(s_to_count)),
                
                ("gpmc_dmareq_n", BV(s_count))
            ], [
                ("csr_dat_r", self.csr.dat_r),
                
                ("s_from_ack", BV(s_from_count)),
                
                ("s_to_stb", BV(s_to_count)),
                ("s_to_data", BV(16*s_to_count)),
                
                ("gpmc_clk", gpmc_pins.clk),
                ("gpmc_a", gpmc_pins.a),
                ("gpmc_we_n", gpmc_pins.we_n),
                ("gpmc_oe_n", gpmc_pins.oe_n),
                ("gpmc_ale_n", gpmc_pins.ale_n),
                
                ("gpmc_csr_cs_n", csr_cs_pin),
                ("gpmc_dma_cs_n", dma_cs_pin)
            ], [
                ("gpmc_d", gpmc_pins.d)
            ], [
                ("s_from_count", s_from_count),
                ("s_to_count", s_to_count)
            ],
            clkport="sys_clk",
            rstport="sys_rst"
        )
    
    def get_fragment(self):
        comb = []
        
        if self._streams_from:
            from_stbs = [s.stb for s in self._streams_from]
            from_acks = [s.ack for s in self._streams_from]
            from_datas = [s.data for s in self._streams_from]
            comb += [
                Cat(*from_stbs).eq(self._inst.outs["s_from_stb"]),
                self._inst.ins["s_from_ack"].eq(Cat(*from_acks)),
                Cat(*from_datas).eq(self._inst.outs["s_from_data"])
            ]
            
        if self._streams_to:
            to_stbs = [s.stb for s in self._streams_to]
            to_acks = [s.ack for s in self._streams_to]
            to_datas = [s.data for s in self._streams_to]
            comb += [
                self._inst.ins["s_to_stb"].eq(Cat(*to_stbs)),
                Cat(*to_acks).eq(self._inst.outs["s_to_ack"]),
                self._inst.ins["s_to_data"].eq(Cat(*to_datas)),
            ]
            
        if self._dmareq_pins:
            comb.append(Cat(*self._dmareq_pins).eq(self._inst.outs["gpmc_dmareq_n"]))
        
        return Fragment(comb, instances=[self._inst])

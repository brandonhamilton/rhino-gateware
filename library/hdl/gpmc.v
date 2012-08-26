module gpmc #(
	parameter s_from_count = 0,
	parameter s_to_count = 0
) (
	/*
	 * System
	 */
	input sys_clk,
	input sys_rst,
	
	/*
	 * CSR
	 */
	output reg [13:0] csr_adr,
	output csr_we,
	input [15:0] csr_dat_r,
	output reg [15:0] csr_dat_w,

	/* Streams
	 * NB: the unused MSB is here to avoid trouble when the
	 * number of ports is 0.
	 */
	/* from GPMC */
	output [s_from_count:0] s_from_stb,
	input [s_from_count:0] s_from_ack,
	output [16*s_from_count:0] s_from_data,
	/* to GPMC */
	input [s_from_count:0] s_to_stb,
	output [s_from_count:0] s_to_ack,
	input [16*s_from_count:0] s_to_data,
	
	/*
	 * GPMC
	 */
	input gpmc_clk,
	input [9:0] gpmc_a,
	inout [15:0] gpmc_d,
	input gpmc_we_n,
	input gpmc_oe_n,
	input gpmc_ale_n,
	
	input gpmc_csr_cs_n,
	input gpmc_dma_cs_n,
	output [s_from_count+s_to_count:0] gpmc_dmareq_n /* < unused MSB */
);

/*
 * Register address
 */
reg [25:0] gpmc_ar;
always @(posedge gpmc_clk)
	if(~gpmc_ale_n)
		gpmc_ar <= {gpmc_a, gpmc_d};

/*
 * CSR
 */

/* synchronize address and write data to sys_clk domain */
reg [13:0] csr_adr_0;
reg [15:0] csr_dat_w_0;
// synthesis attribute shreg_extract of csr_adr_0 is no
// synthesis attribute shreg_extract of csr_adr is no
// synthesis attribute shreg_extract of csr_dat_w_0 is no
// synthesis attribute shreg_extract of csr_dat_w is no
always @(posedge sys_clk) begin
	csr_adr_0 <= gpmc_ar[13:0];
	csr_dat_w_0 <= gpmc_d[15:0];
	csr_adr <= csr_adr_0;
	csr_dat_w <= csr_dat_w_0;
end

/* synchronize read data to gpmc_clk domain */
reg [15:0] csr_dat_r_gpmc_0;
reg [15:0] csr_dat_r_gpmc;
// synthesis attribute shreg_extract of csr_dat_r_gpmc_0 is no
// synthesis attribute shreg_extract of csr_dat_r_gpmc is no
always @(posedge gpmc_clk) begin
	csr_dat_r_gpmc_0 <= csr_dat_r;
	csr_dat_r_gpmc <= csr_dat_r_gpmc_0;
end

/* synchronize write pulse */
wire csr_wp_gpmc;
psync sync_csr_we(
	.clk1(gpmc_clk),
	.i(csr_wp_gpmc),
	.clk2(sys_clk),
	.o(csr_we)
);

/* generate write pulse */
wire csr_we_gpmc;
reg csr_we_gpmc_r;

assign csr_we_gpmc = ~gpmc_csr_cs_n & gpmc_ale_n & ~gpmc_we_n;
always @(posedge gpmc_clk)
	csr_we_gpmc_r <= csr_we_gpmc;

assign csr_wp_gpmc = csr_we_gpmc & ~csr_we_gpmc_r;

/* drive read data */
assign gpmc_d = (~gpmc_csr_cs_n & ~gpmc_oe_n & gpmc_ale_n) ? csr_dat_r_gpmc : 16'hzzzz;

endmodule

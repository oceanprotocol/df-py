from df_py.volume.reward_calc_main import RewardCalculator

# globals with compact names, to keep tests compact & readable
C1, C2, C3 = 7, 137, 1285  # chainIDs
NA, NB, NC, ND = "0xnfta_addr", "0xnftb_addr", "0xnftc_addr", "0xnftd_addr"
LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "0xlp4_addr"
LP5 = "0xlp4_addr"
OCN_SYMB, H2O_SYMB = "OCEAN", "H2O"
OCN_ADDR, H2O_ADDR = "0xocean", "0xh2o"
OCN_ADDR2, H2O_ADDR2 = "0xocean2", "0xh2o2"
SYMBOLS = {
    C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
    C2: {OCN_ADDR2: OCN_SYMB, H2O_ADDR2: H2O_SYMB},
}
APPROVED_TOKEN_ADDRS = {C1: [OCN_ADDR, H2O_ADDR], C2: [OCN_ADDR2, H2O_ADDR2]}
DF_WEEK = 7
RATES = {"OCEAN": 0.5, "H2O": 1.6, "PSDN": 0.01}


#mock
class MockRewardCalculator(RewardCalculator):
    def __init__(self):
        return super().__init__({}, {}, {}, {}, {}, {}, DF_WEEK, False, False, False)

    def set_mock_attribute(self, attr_name, attr_value):
        self._freeze_attributes = False
        setattr(self, attr_name, attr_value)
        self._freeze_attributes = True

    def set_V_USD(self, V_USD):
        self.set_mock_attribute("V_USD", V_USD)

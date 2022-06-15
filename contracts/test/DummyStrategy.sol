// SPDX-License-Identifier: (Apache-2.0 AND CC-BY-4.0)
pragma solidity 0.8.12;
import "../interfaces/IDFRewards.sol";

contract DummyStrategy {
    IDFRewards dfrewards;

    constructor(address _dfrewards) {
        dfrewards = IDFRewards(_dfrewards);
    }

    function claim(address tokenAddress, address from) public {
        dfrewards.claimForStrat(from, tokenAddress); // claim rewards for strategy
    }
}

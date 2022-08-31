// SPDX-License-Identifier: (Apache-2.0 AND CC-BY-4.0)
pragma solidity ^0.8.12;

import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/IERC20.sol";
import "../interfaces/IVeOCEAN.sol";



contract veLocker {
    IVeOCEAN veOCEAN;
    IERC20 OCEAN;

    constructor(address _veOCEAN,address _OCEAN) {
        veOCEAN = IVeOCEAN(_veOCEAN);
        OCEAN = IERC20(_OCEAN);
    }

    function create_lock(uint256 value, uint256 unlock_time) public {
        OCEAN.approve(address(veOCEAN), value);
        veOCEAN.create_lock(value, unlock_time);
    }
}

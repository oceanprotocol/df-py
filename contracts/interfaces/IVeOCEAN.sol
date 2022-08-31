// SPDX-License-Identifier: (Apache-2.0 AND CC-BY-4.0)
pragma solidity ^0.8.12;

interface IVeOCEAN {
    function deposit_for(address _address, uint256 _amount) external;
    function create_lock(uint256 value, uint256 unlock_time) external;
}
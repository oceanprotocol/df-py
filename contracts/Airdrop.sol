pragma solidity 0.8.12;
// SPDX-License-Identifier: (Apache-2.0 AND CC-BY-4.0)


import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/IERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/utils/SafeERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/utils/math/SafeMath.sol";
import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/access/Ownable.sol";

contract Airdrop is Ownable {

    using SafeERC20 for IERC20;
    using SafeMath for uint256;

    event Allocated(address[] tos, uint256[] values);
    event Claimed(address to, uint256 value);
    
    mapping(address => uint256) balances;

    // eg OCEAN token
    IERC20 public token;

    constructor(address token_address) public {
	token = IERC20(token_address);
    }

    // Caller calls token.safeApprove(contract_addr, sum(values)),
    // then it calls this function. Anyone can call this, if can they fund it!
    function allocate(address[] calldata tos, uint256[] calldata values)
	external
	returns (bool success)
    {
	require(tos.length == values.length, "Lengths must match");

	uint256 total_value = 0.0;
	for (uint i = 0; i < values.length; i += 1) {
            require(tos[i] != address(0), "Address invalid");
            require(values[i] > 0, "Value invalid");	 
	    balances[tos[i]].add(values[i]);
	    total_value = total_value + values[i];
        }

	token.safeTransferFrom(msg.sender, address(this), total_value);

	emit Allocated(tos, values);
	return true;
    }

    function claimable(address to) external view returns (uint256 value) {
	return balances[to];
    }
    
    // Recipient claims for themselves
    function claim() external returns (bool success) {
	claim(msg.sender);
	return true;
    }

    // Others claim on behalf of recipient
    function claim(address to) public returns (bool success) {
	uint256 value = balances[to];
	require (value > 0, "Nothing to claim");
	balances[address(this)] = balances[address(this)].sub(value);
	token.safeTransfer(to, value);
	balances[to] = balances[to].add(value);
	emit Claimed(to, value);
	return true;
    }
}
    

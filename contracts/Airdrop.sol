pragma solidity 0.8.12;
// SPDX-License-Identifier: (Apache-2.0 AND CC-BY-4.0)


import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/IERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/utils/SafeERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/security/ReentrancyGuard.sol";
import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/access/Ownable.sol";

contract Airdrop is Ownable, ReentrancyGuard {

    using SafeERC20 for IERC20;

    event Allocated(address[] tos, uint256[] values);
    event Claimed(address to, uint256 value);

    IERC20 public token;

    mapping(address => uint256) balances;

    constructor(address token_address) public {
	token = IERC20(token_address);
    }

    function getToken() public view returns (address) {
	return address(token);
    }

    // Caller calls token.safeApprove(contract_addr, sum(values)),
    // then it calls this function. Anyone can call this, if can they fund it!
    function allocate(address[] calldata _tos, uint256[] calldata _values)
	external onlyOwner returns (bool)
    {
	require(_tos.length == _values.length, "Lengths must match");

	uint256 total_value = 0.0;
	for (uint i = 0; i < _values.length; i += 1) {
            require(_tos[i] != address(0), "Address invalid");
            require(_values[i] > 0, "Value invalid");
	    balances[_tos[i]] += _values[i];
	    total_value += _values[i];
        }

	token.safeTransferFrom(msg.sender, address(this), total_value);

	emit Allocated(_tos, _values);
	return true;
    }

    function claimable(address _to) public view returns (uint256) {
	return balances[_to];
    }
    
    // Recipient claims for themselves
    function claim() external returns (bool) {
	claimFor(msg.sender);
	return true;
    }

    // Others claim on behalf of recipient
    function claimFor(address _to) public nonReentrant returns (bool) {
	uint256 amt = balances[_to];
	require (amt > 0, "Nothing to claim");
	balances[_to] = 0;
	token.safeTransfer(_to, amt);
	emit Claimed(_to, amt);
	return true;
    }
}
    

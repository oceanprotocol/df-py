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
    function allocate(address[] calldata _tos, uint256[] calldata _values)
	external returns (bool)
    {
	require(_tos.length == _values.length, "Lengths must match");

	uint256 total_value = 0.0;
	for (uint i = 0; i < _values.length; i += 1) {
            require(_tos[i] != address(0), "Address invalid");
            require(_values[i] > 0, "Value invalid");
	    address to = _tos[i];
	    uint256 value = _values[i];
	    balances[to].add(value);
	    total_value = total_value + value;
        }

	token.safeTransferFrom(msg.sender, address(this), total_value);

	emit Allocated(_tos, _values);
	return true;
    }

    // We can allocate just one address as well
    function allocate1(address _to, uint256 _value) external returns (bool)
    {
	require(_to != address(0), "Address invalid");
	require(_value > 0, "Value invalid");
	balances[_to].add(_value);
	token.safeTransferFrom(msg.sender, address(this), _value);
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
    function claimFor(address _to) public returns (bool) {
	uint256 value = balances[_to];
	require (value > 0, "Nothing to claim");
	balances[address(this)] = balances[address(this)].sub(value);
	token.safeTransfer(_to, value);
	balances[_to] = balances[_to].add(value);
	emit Claimed(_to, value);
	return true;
    }
}
    

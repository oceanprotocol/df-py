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

    // token address => user address => balance
    mapping(address => mapping(address => uint256)) balances;
    mapping(address => uint256) allocated;

    // Caller calls token.safeApprove(contract_addr, sum(values)),
    // then it calls this function. Anyone can call this, if can they fund it!
    function allocate(
        address[] calldata _tos,
        uint256[] calldata _values,
        address tokenAddress
    ) external returns (bool) {
        require(_tos.length == _values.length, "Lengths must match");

        uint256 total_value = 0.0;
        for (uint256 i = 0; i < _values.length; i += 1) {
            require(_tos[i] != address(0), "Address invalid");
            require(_values[i] > 0, "Value invalid");
            balances[tokenAddress][_tos[i]] += _values[i];
            total_value += _values[i];
        }

        IERC20(tokenAddress).safeTransferFrom(
            msg.sender,
            address(this),
            total_value
        );

        allocated[tokenAddress] = allocated[tokenAddress] + total_value;

        emit Allocated(_tos, _values);
        return true;
    }

    function claimables(address _to, address[] calldata tokenAddresses)
        external
        view
        returns (uint256[] memory result)
    {
        result = new uint256[](tokenAddresses.length);
        for (uint256 i = 0; i < tokenAddresses.length; i += 1) {
            result[i] = claimable(_to, tokenAddresses[i]);
        }
        return result;
    }

    function claimable(address _to, address tokenAddress)
        public
        view
        returns (uint256)
    {
        return balances[tokenAddress][_to];
    }

    function claimMultiple(address _to, address[] calldata tokenAddresses)
        public
    {
        for (uint256 i = 0; i < tokenAddresses.length; i++) {
            claimFor(_to, tokenAddresses[i]);
        }
    }

    // Recipient claims for themselves
    function claim(address[] calldata tokenAddresses) external returns (bool) {
        claimMultiple(msg.sender, tokenAddresses);
        return true;
    }

    // Others claim on behalf of recipient
    function claimFor(address _to, address tokenAddress)
        public
        nonReentrant
        returns (bool)
    {
        uint256 amt = balances[tokenAddress][_to];
        require(amt > 0, "Nothing to claim");
        balances[tokenAddress][_to] = 0;
        IERC20(tokenAddress).safeTransfer(_to, amt);
        allocated[tokenAddress] = allocated[tokenAddress] - amt;
        emit Claimed(_to, amt);
        return true;
    }

    /*
     * @dev Withdraw any ERC20 token from the contract except the airdrop token.
     * @param _amount The amount of tokens to withdraw.
     * @param _token The token address to withdraw.
     */
    function withdrawERCToken(uint256 amount, address _token)
        external
        onlyOwner
    {
        require(
            IERC20(_token).balanceOf(address(this)) - amount >=
                allocated[_token],
            "Cannot withdraw allocated token"
        );
        IERC20(_token).transfer(msg.sender, amount);
    }

    // Don't allow eth transfers
    fallback() external {
        revert("Invalid ether transfer");
    }
}

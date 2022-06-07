// SPDX-License-Identifier: (Apache-2.0 AND CC-BY-4.0)
pragma solidity 0.8.12;

import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/ERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/access/Ownable.sol";

// burns half of the tokens on transfer.

contract Badtoken is ERC20, ERC20Burnable, Ownable {

    uint8 _decimals = 18;

    function decimals() public view virtual override returns (uint8) {
        return _decimals;
    }

    constructor(
        string memory _symbol,
        string memory _name,
        uint8 __decimals,
        uint256 _totalSupply
    ) ERC20(_name, _symbol) {
        _mint(msg.sender, _totalSupply);
        _decimals = __decimals;
    }

    function mint(address to, uint256 amount) public onlyOwner {
        _mint(to, amount);
    }

    function transferFrom(
        address from,
        address to,
        uint256 amount
    ) public virtual override returns (bool) {
        uint tfAmount = amount / 2;
        _burn(from, amount - tfAmount);
        address spender = _msgSender();
        _transfer(from, to, tfAmount);
        return true;
    }

    function transfer(address to, uint256 amount) public virtual override returns (bool) {
        uint tfAmount = amount / 2;
        _burn(msg.sender, amount - tfAmount);
        address owner = _msgSender();
        _transfer(owner, to, tfAmount);
        return true;
    }
}

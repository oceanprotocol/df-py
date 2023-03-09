pragma solidity 0.8.12;

contract VestingWallet {
    // taken from https://github.com/oceanprotocol/vw-cli/blob/main/contracts/VestingWalletHalving.sol
    function getAmount(
        uint256 value,
        uint256 t,
        uint256 h
    ) public pure returns (uint256) {
        uint256 p = value >> (t / h);
        t %= h;
        return value - p + (p * t) / h / 2;
    }
}

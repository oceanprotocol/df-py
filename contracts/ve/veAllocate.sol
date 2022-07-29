pragma solidity ^0.8.12;

contract veAllocate {
    mapping(address => mapping(address => mapping(uint256 => uint256))) private veAllocation;
    mapping(address => uint256) private _totalAllocation;

    event AllocationSet(
        address indexed sender,
        address indexed nft,
        uint256 indexed chainId,
        uint256 amount
    );

    function getveAllocation(address _address, address _nft, uint256 chainid)
        public
        view
        returns (uint256)
    {
        return veAllocation[_address][_nft][chainid];
    }

    function getTotalAllocation(address _address)
        public
        view
        returns (uint256)
    {
        return _totalAllocation[_address];
    }


    function setAllocation(
        uint256 amount,
        address nft,
        uint256 chainId
    ) external {
        require(amount <= 1000, "BM");

        _totalAllocation[msg.sender] =
            _totalAllocation[msg.sender] +
            amount -
            veAllocation[msg.sender][nft][chainId];

        veAllocation[msg.sender][nft][chainId] = amount;
        emit AllocationSet(msg.sender, nft, chainId, amount);
    }
}

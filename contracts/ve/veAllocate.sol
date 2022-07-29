pragma solidity ^0.8.12;

contract veAllocate {
    mapping(address => mapping(bytes32 => uint256)) veAllocation;
    mapping(address => uint256) allocationCounter;
    mapping(address => mapping(uint256 => bytes32)) allocationToId;
    mapping(address => mapping(bytes32 => uint256)) idToAllocation;
    mapping(address => uint256) _totalAllocation;

    event AllocationSet(
        address indexed sender,
        address indexed addr,
        uint256 chainId,
        uint256 amount,
        bytes32 id
    );

    function getveAllocation(address _address, bytes32 _id)
        public
        view
        returns (uint256)
    {
        // string is {DataNFT Address}-{chain id}
        // returns the allocation perc for given address
        return veAllocation[_address][_id];
    }

    function getTotalAllocation(address _address)
        public
        view
        returns (uint256)
    {
        // string is {DataNFT Address}-{chain id}
        // returns the allocation perc for given address
        return _totalAllocation[_address];
    }

    function setAllocation(
        uint256 amount,
        address addr,
        uint256 chainId
    ) external {
        bytes32 _id = keccak256(abi.encodePacked(addr, "-", chainId));

        require(amount <= 1000, "BM");

        if (veAllocation[msg.sender][_id] == 0) {
            require(amount > 0, "SM");
            allocationToId[msg.sender][allocationCounter[msg.sender]] = _id;
            idToAllocation[msg.sender][_id] = allocationCounter[msg.sender];
            allocationCounter[msg.sender]++;
        }

        _totalAllocation[msg.sender] =
            _totalAllocation[msg.sender] +
            amount -
            veAllocation[msg.sender][_id];

        veAllocation[msg.sender][_id] = amount;
        emit AllocationSet(msg.sender, addr, chainId, amount, _id);
    }

    function getTotalAllocation(
        address _address,
        uint256 limit,
        uint256 skip
    )
        external
        view
        returns (
            bytes32[] memory allocationIds,
            uint256[] memory allocationAmounts
        )
    {
        // array of bytes32
        allocationIds = new bytes32[](allocationCounter[_address]);

        allocationAmounts = new uint256[](allocationCounter[_address]);

        uint256 _limit = 0;
        if (allocationCounter[_address] > limit + skip) {
            _limit = limit;
        } else {
            _limit = allocationCounter[_address] - skip;
        }

        for (uint256 i = skip; i < skip + _limit; i++) {
            allocationIds[i] = allocationToId[_address][i];
            allocationAmounts[i] = veAllocation[_address][
                allocationToId[_address][i]
            ];
        }
    }
}

pragma solidity ^0.8.12;

contract veAllocate {
    mapping(address => mapping(string => uint256)) veAllocation;
    mapping(address => uint256) allocationCounter;
    mapping(address => mapping(uint256 => string)) allocationToId;
    mapping(address => mapping(string => uint256)) idToAllocation;

    function getveAllocation(address _address, string calldata _id)
        public
        view
        returns (uint256)
    {
        // string is {DT Address}-{chain id}
        // returns the allocation perc for given address
        return veAllocation[_address][_id];
    }

    function allocate(uint256 amount, string calldata _id) external {
        require(bytes(_id).length < 50, "Id too long");
        if (veAllocation[msg.sender][_id] == 0) {
            allocationToId[msg.sender][allocationCounter[msg.sender]] = _id;
            idToAllocation[msg.sender][_id] = allocationCounter[msg.sender];
            allocationCounter[msg.sender]++;
        }
        require(veAllocation[msg.sender][_id] + amount <= 1000, "SM");
        veAllocation[msg.sender][_id] = amount;
    }

    function removeAllocation(uint256 amount, string calldata _id) external {
        require(veAllocation[msg.sender][_id] >= amount, "SM");

        veAllocation[msg.sender][_id] -= amount;

        if (veAllocation[msg.sender][_id] == 0) {
            uint256 no = idToAllocation[msg.sender][_id];
            allocationToId[msg.sender][no] = allocationToId[msg.sender][
                allocationCounter[msg.sender] - 1
            ]; // swap last with this one
            idToAllocation[msg.sender][allocationToId[msg.sender][no]] = no; // swap last with this one

            delete allocationToId[msg.sender][
                allocationCounter[msg.sender] - 1
            ];
            delete idToAllocation[msg.sender][_id];
            allocationCounter[msg.sender]--;
        }
    }

    function totalAllocation(
        address _address,
        uint256 limit,
        uint256 skip
    ) external view returns (string[] memory, uint256[] memory) {
        // array of strings
        string[] memory allocationIds = new string[](
            allocationCounter[_address]
        );

        uint256[] memory allocationAmounts = new uint256[](
            allocationCounter[_address]
        );

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
        return (allocationIds, allocationAmounts);
    }
}

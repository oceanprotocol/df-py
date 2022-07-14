pragma solidity ^0.8.12;

contract veAllocate {
    mapping(address => mapping(string => uint256)) veAllocation;
    mapping(address => uint256) allocationCounter;
    mapping(address => mapping(uint256 => string)) allocationToId;

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
        if (veAllocation[msg.sender][_id] == 0) {
            allocationToId[msg.sender][allocationCounter[msg.sender]] = _id;
            allocationCounter[msg.sender]++;
        } else {
            require(veAllocation[msg.sender][_id] + amount <= 1000, "SM");
        }
        veAllocation[msg.sender][_id] = amount;
    }

    function removeAllocation(uint256 amount, string calldata _id) external {
        require(veAllocation[msg.sender][_id] >= amount, "SM");
        veAllocation[msg.sender][_id] -= amount;
    }

    function totalAllocation(address _address)
        external
        view
        returns (
            uint256,
            string[] memory,
            uint256[] memory
        )
    {
        uint256 total = 0;
        // array of strings
        string[] memory allocationIds = new string[](
            allocationCounter[_address]
        );

        uint256[] memory allocationAmounts = new uint256[](
            allocationCounter[_address]
        );

        for (uint256 i = 0; i < allocationCounter[_address]; i++) {
            total += veAllocation[_address][allocationToId[_address][i]];
            allocationIds[i] = allocationToId[_address][i];
            allocationAmounts[i] = veAllocation[_address][
                allocationToId[_address][i]
            ];
        }
        return (total, allocationIds, allocationAmounts);
    }
}

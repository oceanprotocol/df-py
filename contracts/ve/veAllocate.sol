pragma solidity ^0.8.12;

contract veAllocate {
    mapping(address => mapping(string => uint256)) veAllocation;
    mapping(address => uint256) allocationCounter;
    mapping(address => mapping(uint256 => string)) allocationToId;

    event AllocationSet(
        address indexed sender,
        string indexed id,
        uint256 amount
    );
    event AllocationRemoved(address indexed sender, string indexed id);

    function getveAllocation(address _address, string calldata _id)
        public
        view
        returns (uint256)
    {
        // string is {DT Address}-{chain id}
        // returns the allocation perc for given address
        return veAllocation[_address][_id];
    }

    function setAllocation(uint256 amount, string calldata _id) external {
        if (veAllocation[msg.sender][_id] == 0) {
            allocationToId[msg.sender][allocationCounter[msg.sender]] = _id;
            allocationCounter[msg.sender]++;
        } else {
            require(amount <= 1000, "SM");
        }

        if (amount == 0) {
            _removeAllocation(_id);
        } else {
            veAllocation[msg.sender][_id] = amount;
            emit AllocationSet(msg.sender, _id, amount);
        }
    }

    function _removeAllocation(string calldata _id) internal {
        require(veAllocation[msg.sender][_id] > 0, "SM");
        veAllocation[msg.sender][_id] = 0;

        emit AllocationRemoved(msg.sender, _id);
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

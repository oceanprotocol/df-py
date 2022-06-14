interface IPool {
    function getBaseTokenAddress() external view returns (address);

    function joinswapExternAmountIn(
        uint256 tokenAmountIn,
        uint256 minPoolAmountOut
    ) external returns (uint256 poolAmountOut);
}

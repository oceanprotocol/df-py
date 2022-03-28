// SPDX-License-Identifier: (Apache-2.0 AND CC-BY-4.0)

pragma solidity ^0.8.12;
pragma experimental ABIEncoderV2;
import "OpenZeppelin/openzeppelin-contracts@4.5.0/contracts/cryptography/MerkleProof.sol";
import "OpenZeppelin/openzeppelin-contracts@4.5.0/contracts/token/ERC20/IERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@4.5.0/contracts/token/ERC20/SafeERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@4.5.0/contracts/math/SafeMath.sol";
import "OpenZeppelin/openzeppelin-contracts@4.5.0/contracts/proxy/Initializable.sol";
import "OpenZeppelin/openzeppelin-contracts@4.5.0/contracts/access/Ownable.sol";

/*
Contracts is from https://medium.com/mochilab/merkle-airdrop-one-of-the-best-airdrop-solution-for-token-issues-e2279df1c5c1

About the logic of the contract:

- The tranches variable stores the id of the Airdrop (we can open different airdrops)
- Mapping merkelRoots stores the Merkle Root value of the respective Airdrop.
- Mapping claimed is used to check if in a specific airdrop the address has been claimed or not?
- The seedNewAllocations function is the init function of the Airdrop, after the end of the airdrop registration, the owner of the contract will call this function to transfer the token to the contract as well as save the Merkle Root value.
- The private _claimWeek function will check the conditions to see if the user’s address has been claimed or not? Is the tranches id valid or not?
- The _verifyClaim function will rely on the Merkle Proof submitted by the user to calculate whether the address is correct or not.
- Finally, the _disburse function is the function that will send the token from the contract to the user when all conditions are satisfied.

*/

contract PhoneAirdrop is Ownable {
    using SafeERC20 for IERC20;
    using SafeMath for uint256;
 
    event Claimed(address claimant, uint256 week, uint256 balance);
    event TrancheAdded(uint256 tranche, bytes32 merkleRoot, uint256 totalAmount);
    event TrancheExpired(uint256 tranche);
    event RemovedFunder(address indexed _address);

    IERC20 public token;
    mapping(uint256 => bytes32) public merkleRoots;
    mapping(uint256 => mapping(address => bool)) public claimed;
    uint256 public tranches;
    
    constructor(IERC20 _token) public {
	token = _token;
    }
    
    function seedNewAllocations(
				bytes32 _merkleRoot, uint256 _totalAllocation
				)
	public
	onlyOwner
	returns (uint256 trancheId)
    {
	token.safeTransferFrom(msg.sender, address(this), _totalAllocation);
	trancheId = tranches;
	merkleRoots[trancheId] = _merkleRoot;
	tranches = tranches.add(1);
	emit TrancheAdded(trancheId, _merkleRoot, _totalAllocation);
    }
    
    function expireTranche(
			   uint256 _trancheId
			   )
	public
	onlyOwner
    {
	merkleRoots[_trancheId] = bytes32(0);
	emit TrancheExpired(_trancheId);
    }
    
    function claimWeek(
		       address _liquidityProvider,
		       uint256 _tranche,
		       uint256 _balance,
		       bytes32[] memory _merkleProof
		       )
	public
    {
	_claimWeek(_liquidityProvider, _tranche, _balance, _merkleProof);
	_disburse(_liquidityProvider, _balance);
    }
    
    function claimWeeks(
			address _liquidityProvider,
			uint256[] memory _tranches,
			uint256[] memory _balances,
			bytes32[][] memory _merkleProofs
			)
	public
    {
	uint256 len = _tranches.length;
	require(len == _balances.length && len == _merkleProofs.length, "Mismatching inputs");
	uint256 totalBalance = 0;
	for(uint256 i = 0; i < len; i++) {
	    _claimWeek(_liquidityProvider, _tranches[i], _balances[i], _merkleProofs[i]);
	    totalBalance = totalBalance.add(_balances[i]);
	}
	_disburse(_liquidityProvider, totalBalance);
    }
    
    function verifyClaim(
			 address _liquidityProvider,
			 uint256 _tranche,
			 uint256 _balance,
			 bytes32[] memory _merkleProof
			 )
	public
	view
	returns (bool valid)
    {
	return _verifyClaim(_liquidityProvider, _tranche, _balance, _merkleProof);
    }
    
    function _claimWeek(
			address _liquidityProvider,
			uint256 _tranche,
			uint256 _balance,
			bytes32[] memory _merkleProof
			)
	
	private
    {
	require(_tranche < tranches, "Week cannot be in the future");
	require(!claimed[_tranche][_liquidityProvider], "LP has already claimed");
	require(_verifyClaim(_liquidityProvider, _tranche, _balance, _merkleProof), "Incorrect merkle proof");
	claimed[_tranche][_liquidityProvider] = true;
	emit Claimed(_liquidityProvider, _tranche, _balance);
    }
    
    function _verifyClaim(
			  address _liquidityProvider,
			  uint256 _tranche,
			  uint256 _balance,
			  bytes32[] memory _merkleProof
			  )
	private
	view
	returns (bool valid)
    {
	bytes32 leaf = keccak256(abi.encodePacked(_liquidityProvider, _balance));
	return MerkleProof.verify(_merkleProof, merkleRoots[_tranche], leaf);
    }
    
    function _disburse(
		       address _liquidityProvider,
		       uint256 _balance
		       )
	private
    {
	if (_balance > 0) {
	    token.safeTransfer(_liquidityProvider, _balance);
	} else {
	    revert("No balance would be transferred - not going to waste your gas");
	}
    }
}

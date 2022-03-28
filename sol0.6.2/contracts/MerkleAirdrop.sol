// SPDX-License-Identifier: (Apache-2.0 AND CC-BY-4.0)
// Contract is lightly adapted from https://medium.com/mochilab/merkle-airdrop-one-of-the-best-airdrop-solution-for-token-issues-e2279df1c5c1


pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;
import "OpenZeppelin/openzeppelin-contracts@3.0.1/contracts/cryptography/MerkleProof.sol";
import "OpenZeppelin/openzeppelin-contracts@3.0.1/contracts/token/ERC20/IERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@3.0.1/contracts/token/ERC20/SafeERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@3.0.1/contracts/math/SafeMath.sol";
import "OpenZeppelin/openzeppelin-contracts@3.0.1/contracts/access/Ownable.sol";

contract MerkleAirdrop is Ownable {
    using SafeERC20 for IERC20;
    using SafeMath for uint256;
 
    event Claimed(address claimant, uint256 tranche, uint256 balance);
    event TrancheAdded(uint256 tranche, bytes32 merkleRoot, uint256 totalAmount);
    event TrancheExpired(uint256 tranche);
    event RemovedFunder(address indexed _address);

    // eg OCEAN token
    IERC20 public token;

    // [tranche] : Merkle root
    mapping(uint256 => bytes32) public merkleRoots;

    // [tranche][address] : claimed
    mapping(uint256 => mapping(address => bool)) public claimed;

    // current tranche id. Increments with each new allocation of rewards
    uint256 public tranches;
    
    constructor(IERC20 _token) public {
	token = _token;
    }

    // OPF calls this to initialize a new tranche (airdrop round).
    function seedNewAllocations(bytes32 _merkleRoot, uint256 _totalAllocation)
	public onlyOwner
	returns (uint256 trancheId)
    {
	token.safeTransferFrom(msg.sender, address(this), _totalAllocation);
	trancheId = tranches;
	merkleRoots[trancheId] = _merkleRoot;
	tranches = tranches.add(1);
	emit TrancheAdded(trancheId, _merkleRoot, _totalAllocation);
    }

    // OPF calls this to retire a given tranche, therefore no longer claimable
    function expireTranche(uint256 _trancheId)
	public onlyOwner
    {
	merkleRoots[_trancheId] = bytes32(0);
	emit TrancheExpired(_trancheId);
    }

    // An LP can call this to get OCEAN for a given tranche (e.g. week)
    function claimTranche(address _liquidityProvider,
			  uint256 _tranche,
			  uint256 _balance,
			  bytes32[] memory _merkleProof)
	public
    {
	_claimTranche(_liquidityProvider, _tranche, _balance, _merkleProof);
	_disburse(_liquidityProvider, _balance);
    }
    
    // An LP can call this to get OCEAN for >=1 tranches (eg weeks)
    function claimTranches(address _liquidityProvider,
			   uint256[] memory _tranches,
			   uint256[] memory _balances,
			   bytes32[][] memory _merkleProofs)
	public
    {
	uint256 len = _tranches.length;
	require(len == _balances.length && len == _merkleProofs.length,
		"Mismatching inputs");
	uint256 totalBalance = 0;
	for(uint256 i = 0; i < len; i++) {
	    _claimTranche(_liquidityProvider, _tranches[i], _balances[i],
			  _merkleProofs[i]);
	    totalBalance = totalBalance.add(_balances[i]);
	}
	_disburse(_liquidityProvider, totalBalance);
    }

    // Is the Merkle Proof submitted by the user (LP) correct?
    function verifyClaim(address _liquidityProvider,
			 uint256 _tranche,
			 uint256 _balance,
			 bytes32[] memory _merkleProof)
	public view
	returns (bool valid)
    {
	return _verifyClaim(_liquidityProvider, _tranche, _balance, _merkleProof);
    }

    // Private function - support for claimTranche() and claimTranches()
    function _claimTranche(address _liquidityProvider,
			uint256 _tranche,
			uint256 _balance,
			bytes32[] memory _merkleProof)	
	private
    {
	require(_tranche < tranches, "Tranche cannot be in the future");
	require(!claimed[_tranche][_liquidityProvider], "LP has already claimed");
	require(_verifyClaim(_liquidityProvider, _tranche, _balance, _merkleProof),
		"Incorrect merkle proof");
	claimed[_tranche][_liquidityProvider] = true;
	emit Claimed(_liquidityProvider, _tranche, _balance);
    }
    
    // Private function - support for _claimTranche() and verifyClaim()
    function _verifyClaim(address _liquidityProvider,
			  uint256 _tranche,
			  uint256 _balance,
			  bytes32[] memory _merkleProof)
	private view
	returns (bool valid)
    {
	bytes32 leaf = keccak256(abi.encodePacked(_liquidityProvider, _balance));
	return MerkleProof.verify(_merkleProof, merkleRoots[_tranche], leaf);
    }

    // Disburse funds to LP
    function _disburse(address _liquidityProvider,
		       uint256 _balance)
	private
    {
	if (_balance > 0) {
	    token.safeTransfer(_liquidityProvider, _balance);
	} else {
	    revert("No balance would be transferred - not going to waste your gas");
	}
    }
}

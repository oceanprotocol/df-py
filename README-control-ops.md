# Usage: DFRewards Owner Control Ops


### Contract locations

Contracts are deployed to the same address on each chain:
- DFRewards address: `0x0cea7DA063EA910D6904299b5A29A8b68DBC1947`
- DFStrategy adderss: `0x0000000000cEAe464ae8a73EDDc0B482383490e7`

### What's controlled?

OPF multisig wallets control this DFRewards.sol functionality:

- add strategy
- remove strategy
- withdrawERCToken (unallocated tokens only)
- transfer control to another address

`dftool` can do the above from the command line.

### Info about each multisig wallet, per chain

| chainid | chain name | multisig info in wallets.md | multisig control via Gnosis Safe App | multisig wallet address |
| ------- | ---------- | --------------------------- | ------------------------------------ | ----------------------- |
| 137     | polygon    | [Polygon Gnosis Safe OPF Wallet](https://github.com/oceanprotocol/atlantic/blob/master/logs/wallets.md#polygon-gnosis-safe-opf-wallet) | [App](https://gnosis-safe.io/app/matic:0x6272E00741C16b9A337E29DB672d51Af09eA87dD/home) | `0x6272E00741C16b9A337E29DB672d51Af09eA87dD` |
| 1       | mainnet    | [Mainnet Gnosis Safe OPFC Wallet](https://github.com/oceanprotocol/atlantic/blob/master/logs/wallets.md#mainnet-gnosis-safe-opfc-wallet) | [App](https://gnosis-safe.io/app/eth:0x0d27cd67c4A3fd3Eb9C7C757582f59089F058167/home) | `0x0d27cd67c4A3fd3Eb9C7C757582f59089F058167` |

Further resources:
- Multisig page: https://github.com/oceanprotocol/atlantic/blob/master/logs/wallets.md
- Ocean docs on networks: https://docs.oceanprotocol.com/concepts/networks/

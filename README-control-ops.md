# Usage: DFRewards Owner Control Ops


### Contract locations

Contracts are deploed to the same location on each chain:
- DFRewards: `0x0cea7DA063EA910D6904299b5A29A8b68DBC1947`
- DFStrategy: `0x0000000000cEAe464ae8a73EDDc0B482383490e7`

### What's controlled?

OPF multisig wallets control this DFRewards.sol functionality:

- add strategy
- remove strategy
- withdrawERCToken (unallocated tokens only)
- transfer control to another address

### Wallet info, per chain

| chainid | chain name | wallets.md info | Gnosis Safe App | Gnosis Safe address |
| ------- | ---------- | --------------- | --------------- | ------------------- |
| 137     | polygon    | [Info](https://github.com/oceanprotocol/atlantic/blob/master/logs/wallets.md#polygon-gnosis-safe-opf-wallet) | [App](https://gnosis-safe.io/app/matic:0x6272E00741C16b9A337E29DB672d51Af09eA87dD/home) | `0x6272E00741C16b9A337E29DB672d51Af09eA87dD` |
| 246     | energyweb  | [Info](https://github.com/oceanprotocol/atlantic/blob/master/logs/wallets.md#energyweb-gnosis-safe-opf-wallet)| [App](https://gnosis-safe.io/app/ewt:0xB98f46485e8b9206158D8127BAF81Dbfd6139Cef/home)| `FOO` |
| 1       | mainnet    | [Info]() | [App]() | `FOO` |
| 56      | bsc        | [Info]() | [App]() | `FOO` |
| 1285    | moonriver  |  [Info]() | [App]() | `FOO` |

Further resources:
- Multisig page: https://github.com/oceanprotocol/atlantic/blob/master/logs/wallets.md
- Ocean docs on networks: https://docs.oceanprotocol.com/concepts/networks/

from util.oceanutil import calcDID

# pylint: disable=line-too-long
# Example: https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/ddo/did:op:8d797a40e75a73a9646e48cfb14d5c0f6afb3c897f53403d00787b00e736b9f3

# pylint: disable=line-too-long
golden_data = """did:op:8e31f8f00e66b5ed8d96fe708909112e923b40950e3a01be3ffa0b6e6721fda6,4,0x773fb648F7B93f12a67A9A7D6030993B59D5Bfe7
did:op:4aa86d2c10f9a352ac9ec064122e318d66be6777e9a37c982e46aab144bc0cfa,80001,0xfD10d7F5AA9C65Ced026A25a32858cD0df90ACA8
did:op:ce0380b7a8df53243a6d5e05ee89eb4307b813876bcc0574770dc4be5a96d3f5,4,0xEa5036a89F6D43A979267c3A325915544b791790
did:op:c48a920a73b34472fbc4a691d858c11d99b99905ba403f12a60f8f950c5c7885,80001,0x243Ad0Da364e62752874b95715b1e4a2BE93583f
did:op:510e520591a411f67ec45bf87f54e4a8f4c762a2370b8a7aa31eb3292b7312e9,80001,0x4591Eb557C3c417480Bd50E3486F0F296E474A65
did:op:db5b2cf046012481f0a57f062795d91f856ec3b6247e092821dbb0608fe5b9d9,3,0x5316048188f5Ef7f9A72C9686863525c21f41740
did:op:6aa11b2b141f3a8046a227ccadead4bd093154c5e44a751ebc7ccb1d9f119c8f,1287,0xC0CC7dBfb95E4D42778170fCaA6b82322AA3468d
did:op:9bd243f4f2fc439d095fdee56da00c34bc2d2c1f69f7c84c730f5df2bc61bf3c,1287,0x545512b9b11c3f1030a68dec51b4c47ba9c95e32
did:op:8d797a40e75a73a9646e48cfb14d5c0f6afb3c897f53403d00787b00e736b9f3,4,0xf41eC22779f8a9ac16fC0707744dD8815b50EC48"""


def test_calcDID():
    data = [x.split(",") for x in golden_data.split("\n")]
    for [did, chainID, address] in data:
        chainID = int(chainID)

        assert calcDID(address, chainID) == did

        # address is not case sensitive
        assert calcDID(address.lower(), chainID) == did
        assert calcDID(address.upper(), chainID) == did

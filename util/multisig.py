from safe_cli.operators import safe_operator


def send_multisig_tx(
    to,
    value,
    data,
):
    safe_operator.send_custom(to, value, data)

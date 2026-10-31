from eth_consensus_specs.test.context import spec_state_test, with_heze_and_later
from eth_consensus_specs.test.helpers.deposits import (
    prepare_pending_deposit,
    run_pending_deposit_applying,
)

ADDRESS = b"\x59" * 20


def credentials_with_sweep_threshold(spec, prefix, increments):
    """
    Withdrawal credentials with ``prefix`` carrying ``increments`` units of
    EFFECTIVE_BALANCE_INCREMENT in the sweep threshold bytes.
    """
    offset = spec.SWEEP_THRESHOLD_CREDENTIAL_OFFSET
    length = spec.SWEEP_THRESHOLD_CREDENTIAL_LENGTH
    encoded = int(increments).to_bytes(length, spec.ENDIANNESS)
    return prefix + b"\x00" * (offset - 1) + encoded + b"\x00" * (12 - offset - length) + ADDRESS


def threshold_bytes(spec, validator):
    offset = spec.SWEEP_THRESHOLD_CREDENTIAL_OFFSET
    length = spec.SWEEP_THRESHOLD_CREDENTIAL_LENGTH
    return bytes(validator.withdrawal_credentials[offset : offset + length])


def run_new_validator_deposit(
    spec, state, withdrawal_credentials, amount, expected_threshold, expected_increments
):
    validator_index = len(state.validators)
    pending_deposit = prepare_pending_deposit(
        spec,
        validator_index,
        amount,
        withdrawal_credentials=withdrawal_credentials,
        signed=True,
    )

    yield from run_pending_deposit_applying(spec, state, pending_deposit, validator_index)

    validator = state.validators[validator_index]
    assert spec.get_sweep_threshold(validator) == expected_threshold
    assert threshold_bytes(spec, validator) == int(expected_increments).to_bytes(
        spec.SWEEP_THRESHOLD_CREDENTIAL_LENGTH, spec.ENDIANNESS
    )
    assert bytes(validator.withdrawal_credentials[12:]) == ADDRESS
    assert validator.effective_balance == min(
        amount - amount % spec.EFFECTIVE_BALANCE_INCREMENT, expected_threshold
    )


@with_heze_and_later
@spec_state_test
def test_apply_pending_deposit_compounding_credentials_with_sweep_threshold(spec, state):
    """
    A deposit above the encoded threshold creates a validator whose initial
    effective balance is capped at that threshold.
    """
    increments = 64
    withdrawal_credentials = credentials_with_sweep_threshold(
        spec, spec.COMPOUNDING_WITHDRAWAL_PREFIX, increments
    )
    yield from run_new_validator_deposit(
        spec,
        state,
        withdrawal_credentials,
        amount=spec.Gwei(100_000_000_000),
        expected_threshold=increments * spec.EFFECTIVE_BALANCE_INCREMENT,
        expected_increments=increments,
    )


@with_heze_and_later
@spec_state_test
def test_apply_pending_deposit_compounding_credentials_with_min_sweep_threshold(spec, state):
    increments = spec.MIN_ACTIVATION_BALANCE // spec.EFFECTIVE_BALANCE_INCREMENT
    withdrawal_credentials = credentials_with_sweep_threshold(
        spec, spec.COMPOUNDING_WITHDRAWAL_PREFIX, increments
    )
    yield from run_new_validator_deposit(
        spec,
        state,
        withdrawal_credentials,
        amount=spec.MIN_ACTIVATION_BALANCE,
        expected_threshold=spec.MIN_ACTIVATION_BALANCE,
        expected_increments=increments,
    )


@with_heze_and_later
@spec_state_test
def test_apply_pending_deposit_compounding_credentials_with_max_sweep_threshold(spec, state):
    """
    The maximum threshold is normalised to the zero encoding.
    """
    increments = spec.MAX_EFFECTIVE_BALANCE_ELECTRA // spec.EFFECTIVE_BALANCE_INCREMENT
    withdrawal_credentials = credentials_with_sweep_threshold(
        spec, spec.COMPOUNDING_WITHDRAWAL_PREFIX, increments
    )
    yield from run_new_validator_deposit(
        spec,
        state,
        withdrawal_credentials,
        amount=spec.MIN_ACTIVATION_BALANCE,
        expected_threshold=spec.MAX_EFFECTIVE_BALANCE_ELECTRA,
        expected_increments=0,
    )


@with_heze_and_later
@spec_state_test
def test_apply_pending_deposit_compounding_credentials_without_sweep_threshold(spec, state):
    withdrawal_credentials = credentials_with_sweep_threshold(
        spec, spec.COMPOUNDING_WITHDRAWAL_PREFIX, 0
    )
    yield from run_new_validator_deposit(
        spec,
        state,
        withdrawal_credentials,
        amount=spec.MIN_ACTIVATION_BALANCE,
        expected_threshold=spec.MAX_EFFECTIVE_BALANCE_ELECTRA,
        expected_increments=0,
    )


@with_heze_and_later
@spec_state_test
def test_apply_pending_deposit_compounding_credentials_sweep_threshold_below_min(spec, state):
    """
    An out-of-range threshold is normalised to the default encoding.
    """
    increments = spec.MIN_ACTIVATION_BALANCE // spec.EFFECTIVE_BALANCE_INCREMENT - 1
    withdrawal_credentials = credentials_with_sweep_threshold(
        spec, spec.COMPOUNDING_WITHDRAWAL_PREFIX, increments
    )
    yield from run_new_validator_deposit(
        spec,
        state,
        withdrawal_credentials,
        amount=spec.MIN_ACTIVATION_BALANCE,
        expected_threshold=spec.MAX_EFFECTIVE_BALANCE_ELECTRA,
        expected_increments=0,
    )


@with_heze_and_later
@spec_state_test
def test_apply_pending_deposit_compounding_credentials_sweep_threshold_above_max(spec, state):
    increments = spec.MAX_EFFECTIVE_BALANCE_ELECTRA // spec.EFFECTIVE_BALANCE_INCREMENT + 1
    withdrawal_credentials = credentials_with_sweep_threshold(
        spec, spec.COMPOUNDING_WITHDRAWAL_PREFIX, increments
    )
    yield from run_new_validator_deposit(
        spec,
        state,
        withdrawal_credentials,
        amount=spec.MIN_ACTIVATION_BALANCE,
        expected_threshold=spec.MAX_EFFECTIVE_BALANCE_ELECTRA,
        expected_increments=0,
    )


@with_heze_and_later
@spec_state_test
def test_apply_pending_deposit_eth1_credentials_ignore_sweep_threshold_bytes(spec, state):
    """
    Non-compounding credentials carry no threshold: the bytes are left as they
    are and the threshold is the validator's maximum effective balance.
    """
    increments = 64
    withdrawal_credentials = credentials_with_sweep_threshold(
        spec, spec.ETH1_ADDRESS_WITHDRAWAL_PREFIX, increments
    )
    yield from run_new_validator_deposit(
        spec,
        state,
        withdrawal_credentials,
        amount=spec.Gwei(100_000_000_000),
        expected_threshold=spec.MIN_ACTIVATION_BALANCE,
        expected_increments=increments,
    )

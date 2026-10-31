from eth_consensus_specs.test.context import spec_state_test, with_heze_and_later
from eth_consensus_specs.test.helpers.keys import pubkeys
from eth_consensus_specs.test.helpers.withdrawals import (
    set_compounding_withdrawal_credential_with_balance,
    set_eth1_withdrawal_credential_with_balance,
)

SOURCE_ADDRESS = b"\x22" * 20


def prepare_compounding_validator(spec, state, validator_index, balance=None, threshold=None):
    if balance is None:
        balance = spec.MIN_ACTIVATION_BALANCE
    set_compounding_withdrawal_credential_with_balance(
        spec, state, validator_index, balance=balance, address=SOURCE_ADDRESS
    )
    if threshold is not None:
        spec.set_sweep_threshold(state.validators[validator_index], threshold)


def prepare_set_sweep_threshold_request(
    spec, state, validator_index, threshold, source_address=None
):
    if source_address is None:
        source_address = state.validators[validator_index].withdrawal_credentials[12:]
    return spec.SetSweepThresholdRequest(
        source_address=source_address,
        validator_pubkey=state.validators[validator_index].pubkey,
        threshold=threshold,
    )


def run_set_sweep_threshold_request_processing(spec, state, request, valid=True):
    """
    Run ``process_set_sweep_threshold_request``, yielding:
      - pre-state ('pre')
      - set_sweep_threshold_request ('set_sweep_threshold_request')
      - post-state ('post').

    The function never raises. If valid is False, expect the request to be
    consumed without changing the state.
    """
    pre_state = state.copy()

    yield "pre", state
    yield "set_sweep_threshold_request", request

    spec.process_set_sweep_threshold_request(state, request)

    yield "post", state

    if not valid:
        assert state == pre_state


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__success(spec, state):
    validator_index = 0
    threshold = spec.Gwei(64_000_000_000)
    prepare_compounding_validator(spec, state, validator_index)
    request = prepare_set_sweep_threshold_request(spec, state, validator_index, threshold)

    yield from run_set_sweep_threshold_request_processing(spec, state, request)

    assert spec.get_sweep_threshold(state.validators[validator_index]) == threshold


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__success_min_activation_balance(spec, state):
    validator_index = 0
    threshold = spec.MIN_ACTIVATION_BALANCE
    prepare_compounding_validator(spec, state, validator_index, balance=threshold)
    request = prepare_set_sweep_threshold_request(spec, state, validator_index, threshold)

    yield from run_set_sweep_threshold_request_processing(spec, state, request)

    assert spec.get_sweep_threshold(state.validators[validator_index]) == threshold


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__success_max_effective_balance(spec, state):
    validator_index = 0
    threshold = spec.MAX_EFFECTIVE_BALANCE_ELECTRA
    prepare_compounding_validator(spec, state, validator_index, threshold=spec.Gwei(64_000_000_000))
    request = prepare_set_sweep_threshold_request(spec, state, validator_index, threshold)

    yield from run_set_sweep_threshold_request_processing(spec, state, request)

    assert spec.get_sweep_threshold(state.validators[validator_index]) == threshold


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__unknown_pubkey(spec, state):
    unknown_pubkey = pubkeys[len(state.validators)]
    assert unknown_pubkey not in [validator.pubkey for validator in state.validators]
    request = spec.SetSweepThresholdRequest(
        source_address=SOURCE_ADDRESS,
        validator_pubkey=unknown_pubkey,
        threshold=spec.Gwei(64_000_000_000),
    )

    yield from run_set_sweep_threshold_request_processing(spec, state, request, valid=False)


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__non_compounding_validator(spec, state):
    validator_index = 0
    set_eth1_withdrawal_credential_with_balance(
        spec, state, validator_index, address=SOURCE_ADDRESS
    )
    request = prepare_set_sweep_threshold_request(
        spec, state, validator_index, spec.Gwei(64_000_000_000)
    )

    yield from run_set_sweep_threshold_request_processing(spec, state, request, valid=False)


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__wrong_source_address(spec, state):
    validator_index = 0
    prepare_compounding_validator(spec, state, validator_index)
    request = prepare_set_sweep_threshold_request(
        spec, state, validator_index, spec.Gwei(64_000_000_000), source_address=b"\x42" * 20
    )

    yield from run_set_sweep_threshold_request_processing(spec, state, request, valid=False)


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__exited_validator(spec, state):
    validator_index = 0
    prepare_compounding_validator(spec, state, validator_index)
    state.validators[validator_index].exit_epoch = spec.get_current_epoch(state) + 1
    request = prepare_set_sweep_threshold_request(
        spec, state, validator_index, spec.Gwei(64_000_000_000)
    )

    yield from run_set_sweep_threshold_request_processing(spec, state, request, valid=False)


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__same_threshold(spec, state):
    validator_index = 0
    threshold = spec.Gwei(64_000_000_000)
    prepare_compounding_validator(spec, state, validator_index, threshold=threshold)
    request = prepare_set_sweep_threshold_request(spec, state, validator_index, threshold)

    yield from run_set_sweep_threshold_request_processing(spec, state, request, valid=False)


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__threshold_below_balance(spec, state):
    validator_index = 0
    threshold = spec.Gwei(64_000_000_000)
    prepare_compounding_validator(spec, state, validator_index, balance=threshold + 1)
    request = prepare_set_sweep_threshold_request(spec, state, validator_index, threshold)

    yield from run_set_sweep_threshold_request_processing(spec, state, request, valid=False)


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__threshold_not_increment_multiple(spec, state):
    validator_index = 0
    prepare_compounding_validator(spec, state, validator_index)
    threshold = spec.Gwei(64_000_000_000) + spec.EFFECTIVE_BALANCE_INCREMENT // 2
    request = prepare_set_sweep_threshold_request(spec, state, validator_index, threshold)

    yield from run_set_sweep_threshold_request_processing(spec, state, request, valid=False)


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__threshold_below_min_activation_balance(spec, state):
    validator_index = 0
    threshold = spec.MIN_ACTIVATION_BALANCE - spec.EFFECTIVE_BALANCE_INCREMENT
    prepare_compounding_validator(spec, state, validator_index, balance=threshold)
    request = prepare_set_sweep_threshold_request(spec, state, validator_index, threshold)

    yield from run_set_sweep_threshold_request_processing(spec, state, request, valid=False)


@with_heze_and_later
@spec_state_test
def test_process_set_sweep_threshold_request__threshold_above_max_effective_balance(spec, state):
    validator_index = 0
    prepare_compounding_validator(spec, state, validator_index)
    threshold = spec.MAX_EFFECTIVE_BALANCE_ELECTRA + spec.EFFECTIVE_BALANCE_INCREMENT
    request = prepare_set_sweep_threshold_request(spec, state, validator_index, threshold)

    yield from run_set_sweep_threshold_request_processing(spec, state, request, valid=False)

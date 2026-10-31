from eth_consensus_specs.test.context import spec_state_test, with_heze_and_later
from eth_consensus_specs.test.helpers.withdrawals import (
    assert_process_withdrawals,
    prepare_process_withdrawals,
    set_compounding_withdrawal_credential_with_balance,
)


def run_heze_withdrawals_processing(spec, state):
    yield "pre", state
    spec.process_withdrawals(state)
    yield "post", state


@with_heze_and_later
@spec_state_test
def test_compounding_validator_partial_withdrawal_custom_sweep_threshold(spec, state):
    """
    A compounding validator above its custom sweep threshold is swept down to
    that threshold rather than to MAX_EFFECTIVE_BALANCE_ELECTRA.
    """
    validator_index = 0
    threshold = spec.Gwei(64_000_000_000)
    excess = spec.Gwei(1_000_000_000)

    prepare_process_withdrawals(spec, state, compounding_indices=[validator_index])
    set_compounding_withdrawal_credential_with_balance(
        spec, state, validator_index, effective_balance=threshold, balance=threshold + excess
    )
    spec.set_sweep_threshold(state.validators[validator_index], threshold)
    assert spec.is_partially_withdrawable_validator(
        state.validators[validator_index], state.balances[validator_index]
    )

    pre_state = state.copy()
    yield from run_heze_withdrawals_processing(spec, state)
    assert_process_withdrawals(
        spec,
        state,
        pre_state,
        withdrawal_count=1,
        balances={validator_index: threshold},
        withdrawal_amounts={validator_index: excess},
        withdrawal_index_delta=1,
    )


@with_heze_and_later
@spec_state_test
def test_compounding_validator_below_custom_sweep_threshold_not_swept(spec, state):
    """
    A compounding validator whose effective balance is below its custom sweep
    threshold is not swept.
    """
    validator_index = 0
    threshold = spec.Gwei(128_000_000_000)
    balance = spec.Gwei(100_000_000_000)

    prepare_process_withdrawals(spec, state, compounding_indices=[validator_index])
    set_compounding_withdrawal_credential_with_balance(
        spec, state, validator_index, effective_balance=balance, balance=balance + 1
    )
    spec.set_sweep_threshold(state.validators[validator_index], threshold)
    assert not spec.is_partially_withdrawable_validator(
        state.validators[validator_index], state.balances[validator_index]
    )

    pre_state = state.copy()
    yield from run_heze_withdrawals_processing(spec, state)
    assert_process_withdrawals(
        spec,
        state,
        pre_state,
        withdrawal_count=0,
        no_withdrawal_indices=[validator_index],
    )

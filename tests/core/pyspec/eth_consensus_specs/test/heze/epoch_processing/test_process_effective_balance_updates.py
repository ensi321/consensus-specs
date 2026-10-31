from eth_consensus_specs.test.context import spec_state_test, with_heze_and_later
from eth_consensus_specs.test.helpers.epoch_processing import (
    run_epoch_processing_to,
    run_process_slots_up_to_epoch_boundary,
)
from eth_consensus_specs.test.helpers.withdrawals import set_compounding_withdrawal_credential


@with_heze_and_later
@spec_state_test
def test_effective_balance_capped_at_custom_sweep_threshold(spec, state):
    """
    The effective balance of a compounding validator is capped at its custom
    sweep threshold, while a validator with the default threshold is capped at
    MAX_EFFECTIVE_BALANCE_ELECTRA.
    """
    run_process_slots_up_to_epoch_boundary(spec, state)
    run_epoch_processing_to(
        spec, state, "process_effective_balance_updates", enable_slots_processing=False
    )

    custom_index, default_index = 0, 1
    threshold = spec.Gwei(64_000_000_000)
    balance = spec.Gwei(100_000_000_000)
    for index in (custom_index, default_index):
        set_compounding_withdrawal_credential(spec, state, index)
        state.validators[index].effective_balance = spec.MIN_ACTIVATION_BALANCE
        state.balances[index] = balance
    spec.set_sweep_threshold(state.validators[custom_index], threshold)
    assert spec.get_sweep_threshold(state.validators[default_index]) == (
        spec.MAX_EFFECTIVE_BALANCE_ELECTRA
    )

    yield "pre", state
    spec.process_effective_balance_updates(state)
    yield "post", state

    assert state.validators[custom_index].effective_balance == threshold
    assert state.validators[default_index].effective_balance == balance

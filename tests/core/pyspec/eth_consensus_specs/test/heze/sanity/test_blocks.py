from eth_consensus_specs.test.context import spec_state_test, with_heze_and_later
from eth_consensus_specs.test.helpers.block import build_empty_block_for_next_slot
from eth_consensus_specs.test.helpers.state import state_transition_and_sign_block
from eth_consensus_specs.test.helpers.withdrawals import (
    set_compounding_withdrawal_credential_with_balance,
    set_parent_block_full,
)


@with_heze_and_later
@spec_state_test
def test_set_sweep_threshold_request_in_parent_execution_requests(spec, state):
    """
    A block delivering the parent payload's set sweep threshold request updates
    the validator's sweep threshold.
    """
    validator_index = 0
    source_address = b"\x22" * 20
    threshold = spec.Gwei(64_000_000_000)
    set_compounding_withdrawal_credential_with_balance(
        spec, state, validator_index, balance=spec.MIN_ACTIVATION_BALANCE, address=source_address
    )
    requests = spec.ExecutionRequests(
        sweep_thresholds=spec.SweepThresholdRequests.of(
            spec.SetSweepThresholdRequest(
                source_address=source_address,
                validator_pubkey=state.validators[validator_index].pubkey,
                threshold=threshold,
            )
        ),
    )
    set_parent_block_full(spec, state)
    state.latest_execution_payload_bid.execution_requests_root = spec.hash_tree_root(requests)

    yield "pre", state

    block = build_empty_block_for_next_slot(spec, state)
    block.body.parent_execution_requests = requests
    signed_block = state_transition_and_sign_block(spec, state, block)

    yield "blocks", [signed_block]
    yield "post", state

    assert spec.get_sweep_threshold(state.validators[validator_index]) == threshold

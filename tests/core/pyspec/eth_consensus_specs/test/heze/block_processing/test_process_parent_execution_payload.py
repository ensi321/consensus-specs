from eth_consensus_specs.test.context import (
    expect_assertion_error,
    spec_state_test,
    with_heze_and_later,
)
from eth_consensus_specs.test.helpers.block import build_empty_block_for_next_slot
from eth_consensus_specs.test.helpers.withdrawals import (
    set_compounding_withdrawal_credential_with_balance,
    set_parent_block_full,
)

SOURCE_ADDRESS = b"\x22" * 20


def _prepare_sweep_threshold_requests(spec, state, validator_indices, threshold):
    requests = []
    for validator_index in validator_indices:
        set_compounding_withdrawal_credential_with_balance(
            spec,
            state,
            validator_index,
            balance=spec.MIN_ACTIVATION_BALANCE,
            address=SOURCE_ADDRESS,
        )
        requests.append(
            spec.SetSweepThresholdRequest(
                source_address=SOURCE_ADDRESS,
                validator_pubkey=state.validators[validator_index].pubkey,
                threshold=threshold,
            )
        )
    return spec.ExecutionRequests(sweep_thresholds=spec.SweepThresholdRequests.of(*requests))


def _commit_parent_requests(spec, state, requests):
    set_parent_block_full(spec, state)
    state.latest_execution_payload_bid.execution_requests_root = spec.hash_tree_root(requests)


def run_parent_execution_payload_processing(spec, state, block, valid=True):
    yield "pre", state
    yield "block", block

    if not valid:
        expect_assertion_error(lambda: spec.process_parent_execution_payload(state, block))
        yield "post", None
        return

    spec.process_parent_execution_payload(state, block)
    yield "post", state


@with_heze_and_later
@spec_state_test
def test_process_parent_execution_payload__set_sweep_threshold_request(spec, state):
    validator_index = 0
    threshold = spec.Gwei(64_000_000_000)
    requests = _prepare_sweep_threshold_requests(spec, state, [validator_index], threshold)
    _commit_parent_requests(spec, state, requests)

    block = build_empty_block_for_next_slot(spec, state)
    block.body.parent_execution_requests = requests

    spec.process_slots(state, block.slot)
    yield from run_parent_execution_payload_processing(spec, state, block)

    assert spec.get_sweep_threshold(state.validators[validator_index]) == threshold


@with_heze_and_later
@spec_state_test
def test_process_parent_execution_payload__set_sweep_threshold_requests_at_limit(spec, state):
    threshold = spec.Gwei(64_000_000_000)
    validator_indices = list(range(spec.MAX_SET_SWEEP_THRESHOLD_REQUESTS_PER_PAYLOAD))
    requests = _prepare_sweep_threshold_requests(spec, state, validator_indices, threshold)
    assert len(requests.sweep_thresholds) == spec.MAX_SET_SWEEP_THRESHOLD_REQUESTS_PER_PAYLOAD
    _commit_parent_requests(spec, state, requests)

    block = build_empty_block_for_next_slot(spec, state)
    block.body.parent_execution_requests = requests

    spec.process_slots(state, block.slot)
    yield from run_parent_execution_payload_processing(spec, state, block)

    for validator_index in validator_indices:
        assert spec.get_sweep_threshold(state.validators[validator_index]) == threshold


@with_heze_and_later
@spec_state_test
def test_process_parent_execution_payload__set_sweep_threshold_requests_over_limit(spec, state):
    threshold = spec.Gwei(64_000_000_000)
    validator_indices = list(range(spec.MAX_SET_SWEEP_THRESHOLD_REQUESTS_PER_PAYLOAD + 1))
    requests = _prepare_sweep_threshold_requests(spec, state, validator_indices, threshold)
    _commit_parent_requests(spec, state, requests)

    block = build_empty_block_for_next_slot(spec, state)
    block.body.parent_execution_requests = requests

    spec.process_slots(state, block.slot)
    yield from run_parent_execution_payload_processing(spec, state, block, valid=False)

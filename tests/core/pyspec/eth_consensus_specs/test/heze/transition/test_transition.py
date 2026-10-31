from eth_consensus_specs.test.context import (
    expect_assertion_error,
    ForkMeta,
    with_fork_metas,
)
from eth_consensus_specs.test.helpers.block import build_empty_block, sign_block
from eth_consensus_specs.test.helpers.constants import GLOAS, HEZE
from eth_consensus_specs.test.helpers.deposits import (
    make_withdrawal_credentials,
    prepare_deposit_request,
)
from eth_consensus_specs.test.helpers.execution_payload import (
    build_empty_execution_payload,
    compute_and_sign_execution_payload_bid,
    compute_el_block_hash,
)
from eth_consensus_specs.test.helpers.fork_transition import (
    do_fork,
    state_transition_across_slots,
)
from eth_consensus_specs.test.helpers.state import state_transition_and_sign_block


def _build_last_gloas_block_with_requests(spec, state, slot, execution_requests):
    """
    Build a block at ``slot`` whose payload bid commits to
    ``execution_requests``, which the next block delivers.
    """
    state = state.copy()
    spec.process_slots(state, slot)
    block = build_empty_block(spec, state)
    payload = build_empty_execution_payload(
        spec,
        state,
        randao_mix=spec.get_randao_mix(state, spec.get_current_epoch(state)),
        execution_requests=execution_requests,
    )
    payload.parent_hash = state.latest_block_hash
    payload.block_hash = compute_el_block_hash(spec, payload, state, execution_requests)
    block.body.signed_execution_payload_bid = compute_and_sign_execution_payload_bid(
        spec, state, payload, execution_requests=execution_requests
    )
    return block


def _build_first_heze_block_on_full_parent(post_spec, state, parent_bid, parent_requests):
    """
    Build the first Heze block on the full payload of the last Gloas block,
    delivering ``parent_requests`` upgraded to the Heze type.
    """
    block = build_empty_block(post_spec, state, slot=state.slot)
    bid = block.body.signed_execution_payload_bid.message
    bid.parent_block_hash = parent_bid.block_hash
    bid.block_hash = post_spec.Hash32(b"\x02" + b"\x00" * 31)
    block.body.parent_execution_requests = post_spec.ExecutionRequests(
        deposits=parent_requests.deposits,
        withdrawals=parent_requests.withdrawals,
        consolidations=parent_requests.consolidations,
        builder_deposits=parent_requests.builder_deposits,
        builder_exits=parent_requests.builder_exits,
    )
    return block


def _transition_to_heze_with_full_gloas_parent(spec, state, post_spec, fork_epoch, pre_tag):
    """
    Build blocks up to the last Gloas slot, whose block commits to a deposit
    request, then upgrade the state to Heze. Returns the blocks, the last Gloas
    bid and its requests.
    """
    last_gloas_slot = spec.Uint64(fork_epoch) * spec.SLOTS_PER_EPOCH - 1
    blocks = [
        pre_tag(block) for block in state_transition_across_slots(spec, state, last_gloas_slot - 1)
    ]

    deposit_request = prepare_deposit_request(
        spec,
        validator_index=len(state.validators),
        amount=spec.MIN_ACTIVATION_BALANCE,
        withdrawal_credentials=make_withdrawal_credentials(
            spec, spec.ETH1_ADDRESS_WITHDRAWAL_PREFIX, b"\x56"
        ),
        signed=True,
    )
    requests = spec.ExecutionRequests(deposits=spec.DepositRequests.of(deposit_request))

    block = _build_last_gloas_block_with_requests(spec, state, last_gloas_slot, requests)
    blocks.append(pre_tag(state_transition_and_sign_block(spec, state, block)))
    parent_bid = state.latest_execution_payload_bid.copy()
    assert parent_bid.execution_requests_root == spec.hash_tree_root(requests)

    state, _ = do_fork(state, spec, post_spec, fork_epoch, with_block=False)
    assert state.latest_execution_payload_bid.block_hash == parent_bid.block_hash
    assert state.latest_execution_payload_bid.execution_requests_root == (
        parent_bid.execution_requests_root
    )
    assert state.latest_block_hash != parent_bid.block_hash

    return state, blocks, parent_bid, requests


@with_fork_metas([ForkMeta(pre_fork_name=GLOAS, post_fork_name=HEZE, fork_epoch=2)])
def test_transition_first_heze_block_delivers_gloas_parent_requests(
    state, fork_epoch, spec, post_spec, pre_tag, post_tag
):
    """
    The last Gloas block commits to a payload with a deposit request. The first
    Heze block builds on that full payload and delivers the request. The bid
    commits to the Gloas ``ExecutionRequests`` type, whose root differs from the
    Heze type, so the block is only valid because the commitment is verified
    against the Gloas type.
    """
    yield "pre", state

    state, blocks, parent_bid, requests = _transition_to_heze_with_full_gloas_parent(
        spec, state, post_spec, fork_epoch, pre_tag
    )

    block = _build_first_heze_block_on_full_parent(post_spec, state, parent_bid, requests)
    assert post_spec.hash_tree_root(block.body.parent_execution_requests) != (
        parent_bid.execution_requests_root
    )
    pre_pending_deposits_len = len(state.pending_deposits)

    post_spec.process_block(state, block)
    block.state_root = state.hash_tree_root()
    blocks.append(post_tag(sign_block(post_spec, state, block)))

    assert state.latest_block_hash == parent_bid.block_hash
    assert len(state.pending_deposits) == pre_pending_deposits_len + 1
    assert state.pending_deposits[-1].pubkey == requests.deposits[0].pubkey

    yield "blocks", blocks
    yield "post", state


@with_fork_metas([ForkMeta(pre_fork_name=GLOAS, post_fork_name=HEZE, fork_epoch=2)])
def test_transition_invalid_first_heze_block_sweep_thresholds_for_gloas_parent(
    state, fork_epoch, spec, post_spec, pre_tag, post_tag
):
    """
    A Gloas payload cannot carry set sweep threshold requests, so the first Heze
    block is rejected if it delivers one for its Gloas parent.
    """
    yield "pre", state

    state, blocks, parent_bid, requests = _transition_to_heze_with_full_gloas_parent(
        spec, state, post_spec, fork_epoch, pre_tag
    )

    block = _build_first_heze_block_on_full_parent(post_spec, state, parent_bid, requests)
    block.body.parent_execution_requests.sweep_thresholds = post_spec.SweepThresholdRequests.of(
        post_spec.SetSweepThresholdRequest(
            source_address=post_spec.ExecutionAddress(b"\x22" * 20),
            validator_pubkey=state.validators[0].pubkey,
            threshold=post_spec.Gwei(64_000_000_000),
        )
    )

    expect_assertion_error(lambda: post_spec.process_block(state, block))
    blocks.append(post_tag(sign_block(post_spec, state, block)))

    yield "blocks", blocks
    yield "post", None

from eth_consensus_specs.test.context import (
    large_validator_set,
    low_balances,
    misc_balances,
    spec_test,
    with_custom_state,
    with_phases,
    with_presets,
    with_state,
)
from eth_consensus_specs.test.helpers.constants import (
    GLOAS,
    HEZE,
    MINIMAL,
)
from eth_consensus_specs.test.helpers.heze.fork import (
    HEZE_FORK_TEST_META_TAGS,
    run_fork_test,
)
from eth_consensus_specs.test.helpers.state import (
    next_epoch,
    next_epoch_via_block,
)
from eth_consensus_specs.test.utils import with_meta_tags


@with_phases(phases=[GLOAS], other_phases=[HEZE])
@spec_test
@with_state
@with_meta_tags(HEZE_FORK_TEST_META_TAGS)
def test_fork_base_state(spec, phases, state):
    yield from run_fork_test(phases[HEZE], state)


@with_phases(phases=[GLOAS], other_phases=[HEZE])
@spec_test
@with_state
@with_meta_tags(HEZE_FORK_TEST_META_TAGS)
def test_fork_clears_sweep_threshold_bytes(spec, phases, state):
    """
    The upgrade clears the sweep threshold bytes of compounding credentials and
    leaves the bytes of other credentials alone.
    """
    post_spec = phases[HEZE]
    offset = post_spec.SWEEP_THRESHOLD_CREDENTIAL_OFFSET
    length = post_spec.SWEEP_THRESHOLD_CREDENTIAL_LENGTH
    encoded = (128).to_bytes(length, "little")
    address = b"\x11" * 20
    compounding_index, execution_index = 0, 1
    state.validators[compounding_index].withdrawal_credentials = (
        spec.COMPOUNDING_WITHDRAWAL_PREFIX + encoded + b"\x00" * 9 + address
    )
    state.validators[execution_index].withdrawal_credentials = (
        spec.ETH1_ADDRESS_WITHDRAWAL_PREFIX + encoded + b"\x00" * 9 + address
    )

    yield "pre", state

    post_state = post_spec.upgrade_to_heze(state.copy())

    yield "post", post_state

    compounding = post_state.validators[compounding_index]
    assert bytes(compounding.withdrawal_credentials[offset : offset + length]) == b"\x00" * length
    assert bytes(compounding.withdrawal_credentials[12:]) == address
    assert post_spec.get_sweep_threshold(compounding) == post_spec.MAX_EFFECTIVE_BALANCE_ELECTRA
    execution = post_state.validators[execution_index]
    assert bytes(execution.withdrawal_credentials[offset : offset + length]) == encoded
    for index, validator in enumerate(post_state.validators):
        if index not in (compounding_index, execution_index):
            assert validator == state.validators[index]


@with_phases(phases=[GLOAS], other_phases=[HEZE])
@spec_test
@with_state
@with_meta_tags(HEZE_FORK_TEST_META_TAGS)
def test_fork_next_epoch(spec, phases, state):
    next_epoch(spec, state)
    yield from run_fork_test(phases[HEZE], state)


@with_phases(phases=[GLOAS], other_phases=[HEZE])
@spec_test
@with_state
@with_meta_tags(HEZE_FORK_TEST_META_TAGS)
def test_fork_next_epoch_with_block(spec, phases, state):
    next_epoch_via_block(spec, state)
    yield from run_fork_test(phases[HEZE], state)


@with_phases(phases=[GLOAS], other_phases=[HEZE])
@spec_test
@with_state
@with_meta_tags(HEZE_FORK_TEST_META_TAGS)
def test_fork_many_next_epoch(spec, phases, state):
    for _ in range(3):
        next_epoch(spec, state)
    yield from run_fork_test(phases[HEZE], state)


@with_phases(phases=[GLOAS], other_phases=[HEZE])
@with_custom_state(balances_fn=low_balances, threshold_fn=lambda spec: spec.config.EJECTION_BALANCE)
@spec_test
@with_meta_tags(HEZE_FORK_TEST_META_TAGS)
def test_fork_random_low_balances(spec, phases, state):
    yield from run_fork_test(phases[HEZE], state)


@with_phases(phases=[GLOAS], other_phases=[HEZE])
@with_custom_state(
    balances_fn=misc_balances, threshold_fn=lambda spec: spec.config.EJECTION_BALANCE
)
@spec_test
@with_meta_tags(HEZE_FORK_TEST_META_TAGS)
def test_fork_random_misc_balances(spec, phases, state):
    yield from run_fork_test(phases[HEZE], state)


@with_phases(phases=[GLOAS], other_phases=[HEZE])
@with_presets(
    [MINIMAL],
    reason="mainnet config leads to larger validator set than limit of public/private keys pre-generated",
)
@with_custom_state(
    balances_fn=large_validator_set, threshold_fn=lambda spec: spec.config.EJECTION_BALANCE
)
@spec_test
@with_meta_tags(HEZE_FORK_TEST_META_TAGS)
def test_fork_random_large_validator_set(spec, phases, state):
    yield from run_fork_test(phases[HEZE], state)

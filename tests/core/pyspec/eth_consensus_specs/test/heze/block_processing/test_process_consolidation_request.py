from eth_consensus_specs.test.context import spec_state_test, with_heze_and_later
from eth_consensus_specs.test.helpers.withdrawals import (
    set_eth1_withdrawal_credential_with_balance,
)

ADDRESS = b"\x22" * 20


def run_switch_to_compounding_processing(spec, state, consolidation):
    """
    Run ``process_consolidation_request`` for a switch to compounding, yielding:
      - pre-state ('pre')
      - consolidation_request ('consolidation_request')
      - post-state ('post').
    """
    yield "pre", state
    yield "consolidation_request", consolidation

    spec.process_consolidation_request(state, consolidation)

    yield "post", state


@with_heze_and_later
@spec_state_test
def test_switch_to_compounding_clears_sweep_threshold_bytes(spec, state):
    """
    Switching to compounding credentials clears whatever the threshold bytes
    carried, so the validator starts at the default sweep threshold.
    """
    # move state forward SHARD_COMMITTEE_PERIOD epochs to allow for consolidation
    state.slot += spec.Uint64(spec.config.SHARD_COMMITTEE_PERIOD) * spec.SLOTS_PER_EPOCH
    current_epoch = spec.get_current_epoch(state)
    source_index = spec.get_active_validator_indices(state, current_epoch)[0]

    set_eth1_withdrawal_credential_with_balance(spec, state, source_index, address=ADDRESS)
    validator = state.validators[source_index]
    offset = spec.SWEEP_THRESHOLD_CREDENTIAL_OFFSET
    length = spec.SWEEP_THRESHOLD_CREDENTIAL_LENGTH
    encoded = (128).to_bytes(length, spec.ENDIANNESS)
    validator.withdrawal_credentials = (
        spec.ETH1_ADDRESS_WITHDRAWAL_PREFIX
        + b"\x00" * (offset - 1)
        + encoded
        + b"\x00" * (12 - offset - length)
        + ADDRESS
    )
    assert spec.get_sweep_threshold(validator) == spec.MIN_ACTIVATION_BALANCE

    consolidation = spec.ConsolidationRequest(
        source_address=ADDRESS,
        source_pubkey=validator.pubkey,
        target_pubkey=validator.pubkey,
    )

    yield from run_switch_to_compounding_processing(spec, state, consolidation)

    assert spec.has_compounding_withdrawal_credential(validator)
    assert bytes(validator.withdrawal_credentials[offset : offset + length]) == b"\x00" * length
    assert bytes(validator.withdrawal_credentials[12:]) == ADDRESS
    assert spec.get_sweep_threshold(validator) == spec.MAX_EFFECTIVE_BALANCE_ELECTRA

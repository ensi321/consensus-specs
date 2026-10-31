# Heze -- The Beacon Chain

*Note*: This document is a work-in-progress for researchers and implementers.

<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=6 --minlevel=2 -->

- [Introduction](#introduction)
- [Types](#types)
  - [New `InclusionListBits`](#new-inclusionlistbits)
  - [New `InclusionListCommittee`](#new-inclusionlistcommittee)
  - [New `SweepThresholdRequests`](#new-sweepthresholdrequests)
- [Constants](#constants)
  - [Domains](#domains)
  - [Execution-layer triggered requests](#execution-layer-triggered-requests)
  - [Sweep threshold encoding](#sweep-threshold-encoding)
- [Presets](#presets)
  - [Inclusion list committee](#inclusion-list-committee)
  - [Execution](#execution)
- [Containers](#containers)
  - [New containers](#new-containers)
    - [`InclusionList`](#inclusionlist)
    - [`SignedInclusionList`](#signedinclusionlist)
    - [`SetSweepThresholdRequest`](#setsweepthresholdrequest)
  - [Modified containers](#modified-containers)
    - [`ExecutionPayloadBid`](#executionpayloadbid)
    - [`SignedExecutionPayloadBid`](#signedexecutionpayloadbid)
    - [`BeaconBlockBody`](#beaconblockbody)
    - [`BeaconState`](#beaconstate)
    - [`ExecutionRequests`](#executionrequests)
- [Helpers](#helpers)
  - [Math](#math)
    - [New `bytes_to_uint16`](#new-bytes_to_uint16)
  - [Misc](#misc)
    - [New `get_sweep_threshold`](#new-get_sweep_threshold)
    - [New `set_sweep_threshold`](#new-set_sweep_threshold)
  - [Predicates](#predicates)
    - [New `is_valid_inclusion_list_signature`](#new-is_valid_inclusion_list_signature)
    - [Modified `is_partially_withdrawable_validator`](#modified-is_partially_withdrawable_validator)
  - [Beacon state accessors](#beacon-state-accessors)
    - [New `get_inclusion_list_committee`](#new-get_inclusion_list_committee)
  - [Beacon state mutators](#beacon-state-mutators)
    - [Modified `switch_to_compounding_validator`](#modified-switch_to_compounding_validator)
- [Beacon chain state transition function](#beacon-chain-state-transition-function)
  - [Epoch processing](#epoch-processing)
    - [Modified `apply_pending_deposit`](#modified-apply_pending_deposit)
    - [Modified `process_epoch`](#modified-process_epoch)
    - [Modified `process_effective_balance_updates`](#modified-process_effective_balance_updates)
  - [Block processing](#block-processing)
    - [Modified `process_block`](#modified-process_block)
    - [Withdrawals](#withdrawals)
      - [Modified `get_validators_sweep_withdrawals`](#modified-get_validators_sweep_withdrawals)
    - [Execution payload](#execution-payload)
      - [Modified `get_execution_requests_list`](#modified-get_execution_requests_list)
    - [Operations](#operations)
      - [Modified `process_operations`](#modified-process_operations)
      - [Deposits](#deposits)
        - [Modified `get_validator_from_deposit`](#modified-get_validator_from_deposit)
      - [Execution-layer set sweep threshold requests](#execution-layer-set-sweep-threshold-requests)
        - [New `process_set_sweep_threshold_request`](#new-process_set_sweep_threshold_request)
    - [Parent execution payload](#parent-execution-payload)
      - [Modified `process_parent_execution_payload`](#modified-process_parent_execution_payload)
      - [Modified `apply_parent_execution_payload`](#modified-apply_parent_execution_payload)

<!-- mdformat-toc end -->

## Introduction

Heze is a consensus-layer upgrade containing a number of features. Including:

- [EIP-7805](https://github.com/ethereum/EIPs/blob/9a345f96c2295a678b0ce33e94d41276ddb3fdef/EIPS/eip-7805.md):
  Fork-choice enforced Inclusion Lists (FOCIL)
- [EIP-8015](https://github.com/ethereum/EIPs/blob/0ebff04bf89b696d51ebf2ff9d029940ef3ed693/EIPS/eip-8015.md):
  Remove `deposit` and `eth1data` fields
- [EIP-8148](https://github.com/ethereum/EIPs/blob/59c9869c7bd52f1167be50e86cc3af1e5bb58a19/EIPS/eip-8148.md):
  Custom validator sweep threshold
- [EIP-8365](https://github.com/ethereum/EIPs/blob/718595d75a86eafcf6f005c2b79e23ef941381e5/EIPS/eip-8365.md):
  Disallow new `0x00` validators

*Note*: These EIPs are in draft and may change or be removed. Each link above
points to the specific version targeted by this specification, which may differ
from the latest published version of the EIPs.

## Types

### New `InclusionListBits`

```python
class InclusionListBits(BitVector):
    """
    A bitfield over the inclusion list committee, one bit per member in
    committee order.
    """

    LENGTH = INCLUSION_LIST_COMMITTEE_SIZE
```

### New `InclusionListCommittee`

```python
class InclusionListCommittee(Vector[ValidatorIndex]):
    """
    The inclusion list committee of a slot.
    """

    LENGTH = INCLUSION_LIST_COMMITTEE_SIZE
```

### New `SweepThresholdRequests`

```python
class SweepThresholdRequests(ProgressiveList[SetSweepThresholdRequest]):
    """
    The set-sweep-threshold requests pertaining to a single execution
    payload.
    """
```

## Constants

### Domains

| Name                              | Value                      |
| --------------------------------- | -------------------------- |
| `DOMAIN_INCLUSION_LIST_COMMITTEE` | `DomainType("0x10000000")` |

### Execution-layer triggered requests

| Name                           | Value            |
| ------------------------------ | ---------------- |
| `SWEEP_THRESHOLD_REQUEST_TYPE` | `Bytes1("0x05")` |

### Sweep threshold encoding

| Name                                | Value       |
| ----------------------------------- | ----------- |
| `SWEEP_THRESHOLD_CREDENTIAL_OFFSET` | `Uint64(1)` |
| `SWEEP_THRESHOLD_CREDENTIAL_LENGTH` | `Uint64(2)` |

## Presets

### Inclusion list committee

| Name                            | Value                 |
| ------------------------------- | --------------------- |
| `INCLUSION_LIST_COMMITTEE_SIZE` | `Uint64(2**4)` (= 16) |

### Execution

| Name                                           | Value                 | Description                                                                                            |
| ---------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------ |
| `MAX_SET_SWEEP_THRESHOLD_REQUESTS_PER_PAYLOAD` | `Uint64(2**4)` (= 16) | *[New in Heze:EIP8148]* Maximum number of execution layer set sweep threshold requests in each payload |

## Containers

### New containers

#### `InclusionList`

```python
class InclusionList(Container):
    slot: Slot
    validator_index: ValidatorIndex
    dependent_root: Root
    transactions: Transactions
```

#### `SignedInclusionList`

```python
class SignedInclusionList(Container):
    message: InclusionList
    signature: BLSSignature
```

#### `SetSweepThresholdRequest`

```python
class SetSweepThresholdRequest(Container):
    source_address: ExecutionAddress
    validator_pubkey: BLSPubkey
    threshold: Gwei
```

### Modified containers

#### `ExecutionPayloadBid`

```python
class ExecutionPayloadBid(ProgressiveContainer):
    ACTIVE_FIELDS = active_fields(width=13)

    parent_block_hash: Hash32
    parent_block_root: Root
    block_hash: Hash32
    prev_randao: Bytes32
    fee_recipient: ExecutionAddress
    gas_limit: Uint64
    builder_index: BuilderIndex
    slot: Slot
    value: Gwei
    execution_payment: Gwei
    blob_kzg_commitments: BlobKZGCommitments
    execution_requests_root: Root
    # [New in Heze:EIP7805]
    inclusion_list_bits: InclusionListBits
```

#### `SignedExecutionPayloadBid`

```python
class SignedExecutionPayloadBid(Container):
    # [Modified in Heze:EIP7805]
    message: ExecutionPayloadBid
    signature: BLSSignature
```

#### `BeaconBlockBody`

```python
class BeaconBlockBody(ProgressiveContainer):
    ACTIVE_FIELDS = active_fields(width=13, gaps=(1, 6))

    randao_reveal: BLSSignature
    # [Modified in Heze:EIP8015]
    # Removed `eth1_data`
    graffiti: Bytes32
    proposer_slashings: ProposerSlashings
    attester_slashings: AttesterSlashings
    attestations: Attestations
    # [Modified in Heze:EIP8015]
    # Removed `deposits`
    voluntary_exits: VoluntaryExits
    sync_aggregate: SyncAggregate
    bls_to_execution_changes: BLSToExecutionChanges
    # [Modified in Heze:EIP7805]
    signed_execution_payload_bid: SignedExecutionPayloadBid
    payload_attestations: PayloadAttestations
    parent_execution_requests: ExecutionRequests
```

#### `BeaconState`

```python
class BeaconState(ProgressiveContainer):
    ACTIVE_FIELDS = active_fields(width=46, gaps=(8, 9, 10, 28))

    genesis_time: Uint64
    genesis_validators_root: Root
    slot: Slot
    fork: Fork
    latest_block_header: BeaconBlockHeader
    block_roots: BlockRoots
    state_roots: StateRoots
    historical_roots: HistoricalRoots
    # [Modified in Heze:EIP8015]
    # Removed `eth1_data`
    # [Modified in Heze:EIP8015]
    # Removed `eth1_data_votes`
    # [Modified in Heze:EIP8015]
    # Removed `eth1_deposit_index`
    validators: Validators
    balances: Balances
    randao_mixes: RandaoMixes
    slashings: Slashings
    previous_epoch_participation: EpochParticipation
    current_epoch_participation: EpochParticipation
    justification_bits: JustificationBits
    previous_justified_checkpoint: Checkpoint
    current_justified_checkpoint: Checkpoint
    finalized_checkpoint: Checkpoint
    inactivity_scores: InactivityScores
    current_sync_committee: SyncCommittee
    next_sync_committee: SyncCommittee
    latest_block_hash: Hash32
    next_withdrawal_index: WithdrawalIndex
    next_withdrawal_validator_index: ValidatorIndex
    historical_summaries: HistoricalSummaries
    # [Modified in Heze:EIP8015]
    # Removed `deposit_requests_start_index`
    deposit_balance_to_consume: Gwei
    exit_balance_to_consume: Gwei
    earliest_exit_epoch: Epoch
    consolidation_balance_to_consume: Gwei
    earliest_consolidation_epoch: Epoch
    pending_deposits: PendingDeposits
    pending_partial_withdrawals: PendingPartialWithdrawals
    pending_consolidations: PendingConsolidations
    proposer_lookahead: ProposerLookahead
    builders: Builders
    next_withdrawal_builder_index: BuilderIndex
    execution_payload_availability: ExecutionPayloadAvailability
    builder_pending_payments: BuilderPendingPayments
    builder_pending_withdrawals: BuilderPendingWithdrawals
    # [Modified in Heze:EIP7805]
    latest_execution_payload_bid: ExecutionPayloadBid
    payload_expected_withdrawals: Withdrawals
    ptc_window: PayloadTimelinessCommitteeWindow
```

#### `ExecutionRequests`

```python
class ExecutionRequests(ProgressiveContainer):
    ACTIVE_FIELDS = active_fields(width=6)

    deposits: DepositRequests
    withdrawals: WithdrawalRequests
    consolidations: ConsolidationRequests
    builder_deposits: BuilderDepositRequests
    builder_exits: BuilderExitRequests
    # [New in Heze:EIP8148]
    sweep_thresholds: SweepThresholdRequests
```

## Helpers

### Math

#### New `bytes_to_uint16`

```python
def bytes_to_uint16(data: bytes) -> Uint16:
    """
    Return the integer deserialization of ``data`` interpreted as ``ENDIANNESS``-endian.
    """
    return Uint16(int.from_bytes(data, ENDIANNESS))
```

### Misc

#### New `get_sweep_threshold`

A validator's sweep threshold is stored in its compounding withdrawal
credentials. The `SWEEP_THRESHOLD_CREDENTIAL_LENGTH` bytes starting at
`SWEEP_THRESHOLD_CREDENTIAL_OFFSET`, which are unused before this upgrade, hold
the threshold in units of `EFFECTIVE_BALANCE_INCREMENT`, encoded as a
little-endian integer:

| Bytes    | Contents                                         |
| -------- | ------------------------------------------------ |
| `0`      | `COMPOUNDING_WITHDRAWAL_PREFIX` (`0x02`)         |
| `1..2`   | Threshold in `EFFECTIVE_BALANCE_INCREMENT` units |
| `3..11`  | Reserved                                         |
| `12..31` | Execution address                                |

*Note*: A stored value of `0` means the default threshold,
`MAX_EFFECTIVE_BALANCE_ELECTRA`. A value that is out of range is read as the
default, so that credentials built by tooling unaware of this upgrade, or
carrying a nonsensical value, behave as they did before. For credentials with
any other prefix, the threshold is `get_max_effective_balance(validator)`.

```python
def get_sweep_threshold(validator: Validator) -> Gwei:
    """
    Get the sweep threshold of ``validator``.
    """
    if not has_compounding_withdrawal_credential(validator):
        return get_max_effective_balance(validator)

    start = SWEEP_THRESHOLD_CREDENTIAL_OFFSET
    end = start + SWEEP_THRESHOLD_CREDENTIAL_LENGTH
    increments = bytes_to_uint16(validator.withdrawal_credentials[start:end])
    threshold = Gwei(increments) * EFFECTIVE_BALANCE_INCREMENT

    if threshold < MIN_ACTIVATION_BALANCE:
        return MAX_EFFECTIVE_BALANCE_ELECTRA
    if threshold > MAX_EFFECTIVE_BALANCE_ELECTRA:
        return MAX_EFFECTIVE_BALANCE_ELECTRA

    return threshold
```

#### New `set_sweep_threshold`

*Note*: A threshold of `MAX_EFFECTIVE_BALANCE_ELECTRA` is stored as `0`, so that
every threshold has a single encoding and a validator that sets the maximum has
the same credentials as one that never set a threshold.

```python
def set_sweep_threshold(validator: Validator, threshold: Gwei) -> None:
    """
    Store ``threshold`` in the compounding withdrawal credentials of ``validator``.
    """
    increments = Uint16(0)
    if MIN_ACTIVATION_BALANCE <= threshold < MAX_EFFECTIVE_BALANCE_ELECTRA:
        increments = Uint16(threshold // EFFECTIVE_BALANCE_INCREMENT)

    start = SWEEP_THRESHOLD_CREDENTIAL_OFFSET
    end = start + SWEEP_THRESHOLD_CREDENTIAL_LENGTH
    credentials = validator.withdrawal_credentials
    validator.withdrawal_credentials = Bytes32(
        credentials[:start] + uint_to_bytes(increments) + credentials[end:]
    )
```

### Predicates

#### New `is_valid_inclusion_list_signature`

```python
def is_valid_inclusion_list_signature(
    state: BeaconState, signed_inclusion_list: SignedInclusionList
) -> bool:
    """
    Check if ``signed_inclusion_list`` has a valid signature.
    """
    message = signed_inclusion_list.message
    index = message.validator_index
    pubkey = state.validators[index].pubkey
    domain = compute_domain(
        DOMAIN_INCLUSION_LIST_COMMITTEE,
        compute_fork_version(compute_epoch_at_slot(message.slot)),
        state.genesis_validators_root,
    )
    signing_root = compute_signing_root(message, domain)
    return bls.Verify(pubkey, signing_root, signed_inclusion_list.signature)
```

#### Modified `is_partially_withdrawable_validator`

*Note*: The function `is_partially_withdrawable_validator` is modified to use
the validator's sweep threshold.

```python
def is_partially_withdrawable_validator(validator: Validator, balance: Gwei) -> bool:
    """
    Check if ``validator`` is partially withdrawable.
    """
    # [Modified in Heze:EIP8148]
    sweep_threshold = get_sweep_threshold(validator)
    # [Modified in Heze:EIP8148]
    has_sweep_threshold = validator.effective_balance >= sweep_threshold
    # [Modified in Heze:EIP8148]
    has_excess_balance = balance > sweep_threshold
    return (
        has_execution_withdrawal_credential(validator)
        # [Modified in Heze:EIP8148]
        and has_sweep_threshold
        and has_excess_balance
    )
```

### Beacon state accessors

#### New `get_inclusion_list_committee`

```python
def get_inclusion_list_committee(state: BeaconState, slot: Slot) -> InclusionListCommittee:
    """
    Get the inclusion list committee for the given ``slot``.
    """
    epoch = compute_epoch_at_slot(slot)
    indices: list[ValidatorIndex] = []
    # Concatenate all committees for this slot in order
    committees_per_slot = get_committee_count_per_slot(state, epoch)
    for i in range(committees_per_slot):
        committee = get_beacon_committee(state, slot, CommitteeIndex(i))
        indices.extend(committee)
    return InclusionListCommittee(
        data=[indices[index % len(indices)] for index in range(INCLUSION_LIST_COMMITTEE_SIZE)]
    )
```

### Beacon state mutators

#### Modified `switch_to_compounding_validator`

*Note*: The threshold bytes are cleared so that a validator switching to
compounding credentials starts at the default threshold.

```python
def switch_to_compounding_validator(state: BeaconState, index: ValidatorIndex) -> None:
    validator = state.validators[index]
    validator.withdrawal_credentials = Bytes32(
        COMPOUNDING_WITHDRAWAL_PREFIX + validator.withdrawal_credentials[1:]
    )
    # [New in Heze:EIP8148]
    set_sweep_threshold(validator, MAX_EFFECTIVE_BALANCE_ELECTRA)
    queue_excess_active_balance(state, index)
```

## Beacon chain state transition function

### Epoch processing

#### Modified `apply_pending_deposit`

*Note*: Deposits that would create new validators with BLS withdrawal
credentials are skipped without a refund, including deposits submitted before
Heze. Top-ups to existing validators are unaffected.

```python
def apply_pending_deposit(state: BeaconState, deposit: PendingDeposit) -> None:
    """
    Applies ``deposit`` to the ``state`` without creating validators with BLS withdrawal credentials.
    """
    validator_pubkeys = [validator.pubkey for validator in state.validators]
    if deposit.pubkey not in validator_pubkeys:
        # [New in Heze:EIP8365]
        # Do not create validators with BLS withdrawal credentials
        if deposit.withdrawal_credentials[:1] == BLS_WITHDRAWAL_PREFIX:
            return
        # Verify the deposit signature (proof of possession) which is not checked by the deposit contract
        if is_valid_deposit_signature(
            deposit.pubkey, deposit.withdrawal_credentials, deposit.amount, deposit.signature
        ):
            add_validator_to_registry(
                state, deposit.pubkey, deposit.withdrawal_credentials, deposit.amount
            )
    else:
        validator_index = ValidatorIndex(validator_pubkeys.index(deposit.pubkey))
        increase_balance(state, validator_index, deposit.amount)
```

#### Modified `process_epoch`

*Note*: `process_epoch` removes call to `process_eth1_data_reset`.

```python
def process_epoch(state: BeaconState) -> None:
    process_justification_and_finalization(state)
    process_inactivity_updates(state)
    process_rewards_and_penalties(state)
    process_registry_updates(state)
    process_slashings(state)
    # [Modified in Heze:EIP8015]
    # Removed `process_eth1_data_reset`
    process_pending_deposits(state)
    process_pending_consolidations(state)
    process_builder_pending_payments(state)
    process_effective_balance_updates(state)
    process_slashings_reset(state)
    process_randao_mixes_reset(state)
    process_historical_summaries_update(state)
    process_participation_flag_updates(state)
    process_sync_committee_updates(state)
    process_proposer_lookahead(state)
    process_ptc_window(state)
```

#### Modified `process_effective_balance_updates`

*Note*: The function `process_effective_balance_updates` is modified to cap the
effective balance at the validator's sweep threshold.

```python
def process_effective_balance_updates(state: BeaconState) -> None:
    # Update effective balances with hysteresis
    for index, validator in enumerate(state.validators):
        balance = state.balances[index]
        HYSTERESIS_INCREMENT = Uint64(EFFECTIVE_BALANCE_INCREMENT // HYSTERESIS_QUOTIENT)
        DOWNWARD_THRESHOLD = HYSTERESIS_INCREMENT * HYSTERESIS_DOWNWARD_MULTIPLIER
        UPWARD_THRESHOLD = HYSTERESIS_INCREMENT * HYSTERESIS_UPWARD_MULTIPLIER
        # [Modified in Heze:EIP8148]
        sweep_threshold = get_sweep_threshold(validator)

        if (
            balance + DOWNWARD_THRESHOLD < validator.effective_balance
            or validator.effective_balance + UPWARD_THRESHOLD < balance
        ):
            # [Modified in Heze:EIP8148]
            validator.effective_balance = min(
                balance - balance % EFFECTIVE_BALANCE_INCREMENT, sweep_threshold
            )
```

### Block processing

#### Modified `process_block`

*Note*: `process_block` removes call to `process_eth1_data`.

```python
def process_block(state: BeaconState, block: BeaconBlock) -> None:
    parent_slot = state.latest_block_header.slot

    process_parent_execution_payload(state, block)
    process_block_header(state, block)
    process_withdrawals(state)
    process_execution_payload_bid(state, block.body.signed_execution_payload_bid)
    process_randao(state, block.body)
    # [Modified in Heze:EIP8015]
    # Removed `process_eth1_data`
    process_operations(state, block.body, parent_slot)
    process_sync_aggregate(state, block.body.sync_aggregate)
```

#### Withdrawals

##### Modified `get_validators_sweep_withdrawals`

*Note*: The function `get_validators_sweep_withdrawals` is modified to sweep
each validator down to its sweep threshold.

```python
def get_validators_sweep_withdrawals(
    state: BeaconState,
    withdrawal_index: WithdrawalIndex,
    prior_withdrawals: Sequence[Withdrawal],
) -> tuple[Sequence[Withdrawal], WithdrawalIndex, Uint64]:
    epoch = get_current_epoch(state)
    validators_limit = min(len(state.validators), MAX_VALIDATORS_PER_WITHDRAWALS_SWEEP)
    withdrawals_limit = MAX_WITHDRAWALS_PER_PAYLOAD
    # There must be at least one space reserved for validator sweep withdrawals
    assert len(prior_withdrawals) < withdrawals_limit

    processed_count = Uint64(0)
    withdrawals: list[Withdrawal] = []
    validator_index = state.next_withdrawal_validator_index
    for _ in range(validators_limit):
        all_withdrawals = list(prior_withdrawals) + withdrawals
        has_reached_limit = len(all_withdrawals) >= withdrawals_limit
        if has_reached_limit:
            break

        validator = state.validators[validator_index]
        balance = get_balance_after_withdrawals(state, validator_index, all_withdrawals)
        if is_fully_withdrawable_validator(validator, balance, epoch):
            withdrawals.append(
                Withdrawal(
                    index=withdrawal_index,
                    validator_index=validator_index,
                    address=ExecutionAddress(validator.withdrawal_credentials[12:]),
                    amount=balance,
                )
            )
            withdrawal_index += 1
        elif is_partially_withdrawable_validator(validator, balance):
            withdrawals.append(
                Withdrawal(
                    index=withdrawal_index,
                    validator_index=validator_index,
                    address=ExecutionAddress(validator.withdrawal_credentials[12:]),
                    # [Modified in Heze:EIP8148]
                    amount=balance - get_sweep_threshold(validator),
                )
            )
            withdrawal_index += 1

        validator_index = (validator_index + 1) % len(state.validators)
        processed_count += 1

    return withdrawals, withdrawal_index, processed_count
```

#### Execution payload

##### Modified `get_execution_requests_list`

*Note*: Encodes execution requests as defined by
[EIP-7685](https://eips.ethereum.org/EIPS/eip-7685).

```python
def get_execution_requests_list(execution_requests: ExecutionRequests) -> Sequence[bytes]:
    requests: Sequence[tuple[Bytes1, ProgressiveList]] = [
        (DEPOSIT_REQUEST_TYPE, execution_requests.deposits),
        (WITHDRAWAL_REQUEST_TYPE, execution_requests.withdrawals),
        (CONSOLIDATION_REQUEST_TYPE, execution_requests.consolidations),
        (BUILDER_DEPOSIT_REQUEST_TYPE, execution_requests.builder_deposits),
        (BUILDER_EXIT_REQUEST_TYPE, execution_requests.builder_exits),
        # [New in Heze:EIP8148]
        (SWEEP_THRESHOLD_REQUEST_TYPE, execution_requests.sweep_thresholds),
    ]

    return [
        request_type + ssz_serialize(request_data)
        for request_type, request_data in requests
        if len(request_data) != 0
    ]
```

#### Operations

##### Modified `process_operations`

*Note*: `process_operations` removes the check that `body.deposits` is empty.

```python
def process_operations(state: BeaconState, body: BeaconBlockBody, parent_slot: Slot) -> None:
    def for_ops(operations: Sequence[Any], fn: Callable[..., None], *args: Any) -> None:
        for operation in operations:
            fn(state, operation, *args)

    assert len(body.proposer_slashings) <= MAX_PROPOSER_SLASHINGS
    assert len(body.attester_slashings) <= MAX_ATTESTER_SLASHINGS_ELECTRA
    assert len(body.attestations) <= MAX_ATTESTATIONS_ELECTRA
    assert len(body.voluntary_exits) <= MAX_VOLUNTARY_EXITS
    assert len(body.bls_to_execution_changes) <= MAX_BLS_TO_EXECUTION_CHANGES
    assert len(body.payload_attestations) <= MAX_PAYLOAD_ATTESTATIONS

    for_ops(body.proposer_slashings, process_proposer_slashing)
    for_ops(body.attester_slashings, process_attester_slashing)
    for_ops(body.attestations, process_attestation, parent_slot)
    for_ops(body.voluntary_exits, process_voluntary_exit)
    for_ops(body.bls_to_execution_changes, process_bls_to_execution_change)
    for_ops(body.payload_attestations, process_payload_attestation)
```

##### Deposits

###### Modified `get_validator_from_deposit`

*Note*: The function `get_validator_from_deposit` is modified to store the
threshold of a new compounding validator in its canonical encoding, and to cap
its initial effective balance at that threshold.

```python
def get_validator_from_deposit(
    pubkey: BLSPubkey, withdrawal_credentials: Bytes32, amount: Gwei
) -> Validator:
    validator = Validator(
        pubkey=pubkey,
        withdrawal_credentials=withdrawal_credentials,
        effective_balance=Gwei(0),
        slashed=Boolean(False),
        activation_eligibility_epoch=FAR_FUTURE_EPOCH,
        activation_epoch=FAR_FUTURE_EPOCH,
        exit_epoch=FAR_FUTURE_EPOCH,
        withdrawable_epoch=FAR_FUTURE_EPOCH,
    )

    # [New in Heze:EIP8148]
    if has_compounding_withdrawal_credential(validator):
        set_sweep_threshold(validator, get_sweep_threshold(validator))

    # [Modified in Heze:EIP8148]
    sweep_threshold = get_sweep_threshold(validator)
    validator.effective_balance = min(
        amount - amount % EFFECTIVE_BALANCE_INCREMENT, sweep_threshold
    )

    return validator
```

##### Execution-layer set sweep threshold requests

###### New `process_set_sweep_threshold_request`

*Note*: A request is rejected if its threshold is below the validator's current
balance. This prevents validators from gaming the sweep cycle to bypass the
partial withdrawal queue and perform immediate withdrawals. To lower a
threshold, validators must first request a partial withdrawal, wait for
processing, then set the desired threshold.

```python
def process_set_sweep_threshold_request(
    state: BeaconState, request: SetSweepThresholdRequest
) -> None:
    validator_pubkeys = [validator.pubkey for validator in state.validators]
    if request.validator_pubkey not in validator_pubkeys:
        return

    index = ValidatorIndex(validator_pubkeys.index(request.validator_pubkey))
    validator = state.validators[index]

    if not has_compounding_withdrawal_credential(validator):
        return
    if validator.withdrawal_credentials[12:] != request.source_address:
        return
    if validator.exit_epoch != FAR_FUTURE_EPOCH:
        return
    if get_sweep_threshold(validator) == request.threshold:
        return
    if request.threshold < state.balances[index]:
        return
    if request.threshold % EFFECTIVE_BALANCE_INCREMENT != 0:
        return
    if request.threshold < MIN_ACTIVATION_BALANCE:
        return
    if request.threshold > MAX_EFFECTIVE_BALANCE_ELECTRA:
        return

    set_sweep_threshold(validator, request.threshold)
```

#### Parent execution payload

##### Modified `process_parent_execution_payload`

*Note*: The function `process_parent_execution_payload` is modified to verify
the bid commitment of a pre-Heze parent against the Gloas `ExecutionRequests`
type. The root of the Heze type differs from the Gloas type even for identical
content, and the state only stores the commitment.

```python
def process_parent_execution_payload(state: BeaconState, block: BeaconBlock) -> None:
    bid = block.body.signed_execution_payload_bid.message
    parent_bid = state.latest_execution_payload_bid
    requests = block.body.parent_execution_requests

    if bid.parent_block_hash != parent_bid.block_hash:
        # Parent was EMPTY -- no execution requests expected
        assert requests == ExecutionRequests.empty()
        return

    # Parent was FULL -- verify the bid commitment and apply the payload
    # [Modified in Heze:EIP8148]
    if compute_epoch_at_slot(state.latest_block_header.slot) < state.fork.epoch:
        # The bid of a pre-Heze parent commits to the Gloas `ExecutionRequests` type
        assert len(requests.sweep_thresholds) == 0
        requests_root = hash_tree_root(
            gloas.ExecutionRequests(
                deposits=requests.deposits,
                withdrawals=requests.withdrawals,
                consolidations=requests.consolidations,
                builder_deposits=requests.builder_deposits,
                builder_exits=requests.builder_exits,
            )
        )
    else:
        requests_root = hash_tree_root(requests)
    assert requests_root == parent_bid.execution_requests_root
    apply_parent_execution_payload(state, requests)
```

##### Modified `apply_parent_execution_payload`

*Note*: The function `apply_parent_execution_payload` is modified to process the
set sweep threshold requests of the parent's execution payload.

```python
def apply_parent_execution_payload(
    state: BeaconState,
    requests: ExecutionRequests,
) -> None:
    parent_bid = state.latest_execution_payload_bid
    parent_slot = state.latest_block_header.slot
    parent_epoch = compute_epoch_at_slot(parent_slot)

    assert len(requests.withdrawals) <= MAX_WITHDRAWAL_REQUESTS_PER_PAYLOAD
    assert len(requests.consolidations) <= MAX_CONSOLIDATION_REQUESTS_PER_PAYLOAD
    assert len(requests.builder_deposits) <= MAX_BUILDER_DEPOSIT_REQUESTS_PER_PAYLOAD
    assert len(requests.builder_exits) <= MAX_BUILDER_EXIT_REQUESTS_PER_PAYLOAD
    # [New in Heze:EIP8148]
    assert len(requests.sweep_thresholds) <= MAX_SET_SWEEP_THRESHOLD_REQUESTS_PER_PAYLOAD

    # Settle the builder payment before the requests so that a builder exit
    # request is rejected while the payment is pending
    if parent_epoch == get_current_epoch(state):
        payment_index = SLOTS_PER_EPOCH + parent_slot % SLOTS_PER_EPOCH
        settle_builder_payment(state, payment_index)
    elif parent_epoch == get_previous_epoch(state):
        payment_index = parent_slot % SLOTS_PER_EPOCH
        settle_builder_payment(state, payment_index)
    elif parent_bid.value > 0:
        # Parent is older than the previous epoch, its payment entry has been
        # evicted from builder_pending_payments. Append the withdrawal directly.
        state.builder_pending_withdrawals.append(
            BuilderPendingWithdrawal(
                fee_recipient=parent_bid.fee_recipient,
                amount=parent_bid.value,
                builder_index=parent_bid.builder_index,
            )
        )

    # Process execution requests from parent's payload. The execution
    # requests are processed at state.slot (child's slot), not the parent's slot.
    def for_ops(operations: Sequence[Any], fn: Callable[[BeaconState, Any], None]) -> None:
        for operation in operations:
            fn(state, operation)

    for_ops(requests.deposits, process_deposit_request)
    for_ops(requests.withdrawals, process_withdrawal_request)
    for_ops(requests.consolidations, process_consolidation_request)
    for_ops(requests.builder_deposits, process_builder_deposit_request)
    for_ops(requests.builder_exits, process_builder_exit_request)
    # [New in Heze:EIP8148]
    for_ops(requests.sweep_thresholds, process_set_sweep_threshold_request)

    # Update parent payload availability and latest block hash
    state.execution_payload_availability[parent_slot % SLOTS_PER_HISTORICAL_ROOT] = Boolean(True)
    state.latest_block_hash = parent_bid.block_hash
```

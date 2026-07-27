# Submission Package: Bonded Claim Slashing Vault

## Summary

Bonded Claim Slashing Vault is a standalone GenLayer Intelligent Contract primitive for staking GEN behind externally verifiable claims. A claimant bonds a claim, a separate challenger can bond a dispute, both sides can submit evidence, and validator consensus resolves whether the claim is upheld, refuted, or not resolvable under the claim's verification policy. Deterministic contract code then releases, refunds, rewards, or slashes funds.

This is meant for importers such as reputation registries, insurance protocols, compliance lists, curation markets, agent marketplaces, grant programs, and any protocol that wants public claims backed by economic accountability.

## StudioNet Deployment

- Contract address: `0x294F85B407df89A18ec94D6bE2ce314ce16dC606`
- Deployment transaction: `0xad81446a1831fe252aac3c1db00639779566cd554ba2ee050a352e0b741c5186`
- Receipt status: `FINALIZED`
- Deployment result: `MAJORITY_AGREE`
- Validator votes: 5 agree, 0 disagree

An earlier deployment attempt used a JSON-array string for `--args`, which StudioNet interpreted as one string argument. That failed constructor execution and produced an unusable address: `0x00E6875495a0e80382a1242F47b70178298eE3a0`. It is not part of the submission.

## GenLayer Consensus Use

The contract uses consensus where deterministic code cannot decide the outcome: whether heterogeneous evidence supports or refutes a claim under a natural-language verification policy. Validators receive a bounded prompt containing:

- claim text
- verification policy
- challenge text
- evidence bundle
- strict JSON verdict envelope

Accepted verdicts are `UPHELD`, `REFUTED`, `INCONCLUSIVE`, `EXTERNAL_FAILURE`, `STALE_EVIDENCE`, and `OUT_OF_SCOPE`. The contract normalizes malformed or unsafe validator output into safe non-slashing outcomes.

## Deterministic State Design

The contract deterministically handles:

- claim bond locking
- challenge bond locking
- claimant/challenger role separation
- challenge windows
- resolution deadlines
- bounded evidence submission
- verdict normalization
- slashing and payout math
- double-settlement protection
- unchallenged withdrawal
- cancellation before challenge
- unresolved timeout refunds
- optional callbacks to importing contracts
- JSON view envelopes for builders

Funds are settled before any callback can be sent. The callback is optional and isolated from core settlement.

## Public Surface

Write methods:

- `register_claim(...) payable -> u256`
- `challenge_claim(claim_id, challenge_text) payable`
- `submit_evidence(claim_id, kind, uri_or_text, notes)`
- `resolve_challenge(claim_id)`
- `timeout_unresolved(claim_id)`
- `withdraw_unchallenged(claim_id)`
- `cancel_unchallenged(claim_id)`
- `send_callback(claim_id)`

View methods:

- `get_claim(claim_id)`
- `get_claim_terms(claim_id)`
- `get_evidence(claim_id, index)`
- `claim_status(claim_id)`
- `claim_verdict(claim_id)`
- `resolution_of(claim_id)`
- `stats()`

## Verification Results

Local validation:

```text
genvm-lint check contracts\bonded_claim_slashing_vault.py --json
ok: true
methods: 15
write_methods: 8
view_methods: 7
```

Consumer example validation:

```text
genvm-lint check examples\claim_registry_consumer.py --json
ok: true
methods: 3
```

Direct test suite:

```text
pytest tests/direct/ -q
31 passed
```

StudioNet full-surface test on a fresh deployed instance:

```text
gltest tests/integration/test_full_surface_studionet.py -v -s --network studionet
1 passed
```

StudioNet exact deployed-address test:

```text
gltest tests/integration/test_deployed_contract_surface.py -v -s --network studionet
1 passed
```

The exact deployed-address test wrote against `0x294F85B407df89A18ec94D6bE2ce314ce16dC606` and exercised:

- successful claim registration
- successful challenge from a different account
- successful evidence submission
- successful consensus resolution
- expected callback failure when no callback is configured
- successful unchallenged withdrawal
- successful unchallenged cancellation
- expected invalid evidence failure
- successful unresolved timeout settlement
- reads from all view methods

## Current Deployed Stats

```json
{
  "next_claim_id": "5",
  "open_claims": "2",
  "challenged_claims": "0",
  "resolved_claims": "4",
  "cancelled_claims": "1",
  "total_bonded": "4400000000000000000",
  "total_slashed": "0",
  "total_returned": "4400000000000000000",
  "total_challenger_rewards": "0",
  "balance": "0",
  "treasury": "0x8b998319628DC04e83a3116e74394afa34aA98a3"
}
```

## Why It Is Reusable

Importers do not need to copy evidence review, slashing, challenge, or payout logic. A registry or insurance protocol can register claims, query `claim_status` and `claim_verdict`, or receive `on_claim_resolved(...)` callbacks. The primitive is claim-generic and can support provider attestations, credential claims, reserve claims, compliance claims, safety claims, uptime claims, grant eligibility claims, and listing-quality claims.

## Honest Limit

This version stores submitted evidence text/URIs and lets validators judge that evidence bundle. It does not yet perform contract-side web fetching for every URI. The settlement mechanics, state machine, and exact deployed write surface are tested. A future hardening pass can add per-kind web acquisition without changing the external primitive.

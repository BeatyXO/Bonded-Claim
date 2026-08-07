# Submission Package: Bonded Claim Slashing Vault

## Summary

Bonded Claim Slashing Vault is a standalone GenLayer Intelligent Contract primitive for staking GEN behind externally verifiable claims. A claimant bonds a claim, a separate challenger can bond a dispute, both sides can submit bounded evidence, and validator consensus resolves whether the claim is upheld, refuted, or not resolvable under the claim's verification policy. Deterministic contract code then releases, refunds, rewards, or slashes funds.

This hardened resubmission adds contract-side acquisition of public source material inside `resolve_challenge`. Public URL evidence is fetched before validator adjudication, so settlement no longer depends on party-supplied text or unread URL strings.

### Fix in this resubmission (Joaquin, Aug 4 2026)

`_normalize_resolution` could previously store a resolution with a conclusive verdict (`UPHELD`/`REFUTED`) while `ok=false`, even though `_settle_upheld`/`_settle_refuted` branch on the verdict alone and would still move funds. `ok` and `verdict` are now a single invariant: a conclusive verdict is only kept as conclusive when the model also reported `ok=true`; otherwise the verdict is downgraded to `INCONCLUSIVE` (with `ok=false`) and no settlement occurs. See `_normalize_resolution` in [contracts/bonded_claim_slashing_vault.py](../contracts/bonded_claim_slashing_vault.py). Covered by `test_upheld_with_ok_false_downgrades_to_inconclusive` and `test_refuted_with_ok_false_downgrades_to_inconclusive` in [tests/direct/test_bonded_claim_slashing_vault.py](../tests/direct/test_bonded_claim_slashing_vault.py).

## StudioNet Deployment

- Contract address: `0xd7Ae325d6e45891AEE581a532E80757496b0109E`
- Deployment transaction: `0xe232787c6ec6065e850eb5fd0f53ba66ba76b89c6281bc6dae0d2595cd100e92`
- Receipt status: `ACCEPTED`
- Deployment result: `MAJORITY_AGREE`
- Validator votes: 5 rounds voted (3 `AGREE`, 2 `IDLE`), quorum reached in round 0

Prior (stale) deployment, kept for reference only — does not contain the `ok`/verdict fix and should not be used: address `0x9e32D760c5940D259ffF8a4e257C890279767451`, tx `0xc500b3c275b6387f97dbb3800b9966c166ade332b5139e8fe61c00d9510fccb2`.

## GenLayer Consensus Use

The contract uses consensus where deterministic code cannot decide the outcome: whether independently acquired evidence supports or refutes a claim under a natural-language verification policy. During `resolve_challenge`, the contract builds an enriched evidence bundle:

- `WEB_TEXT`, `WEB_SCREENSHOT`, and `IMAGE_URL` evidence are fetched with `gl.nondet.web.render`.
- fetched source content is capped as `contract_fetched_excerpt`
- failed public source reads are marked `UNREADABLE`
- party text is retained as context but not treated as independent proof
- validators classify the fetched material into one strict verdict envelope

Accepted verdicts are `UPHELD`, `REFUTED`, `INCONCLUSIVE`, `EXTERNAL_FAILURE`, `STALE_EVIDENCE`, and `OUT_OF_SCOPE`. The contract normalizes malformed or unsafe validator output into safe non-slashing outcomes.

## Deterministic State Design

The contract deterministically handles:

- claim bond locking
- challenge bond locking
- claimant/challenger role separation
- challenge windows
- resolution deadlines
- bounded evidence submission
- fetch-status handling for external evidence
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
35 passed
```

StudioNet exact deployed-address test:

```text
gltest tests/integration/test_deployed_contract_surface.py -v -s --network studionet
1 passed
```

The exact deployed-address test wrote against `0xd7Ae325d6e45891AEE581a532E80757496b0109E` and exercised:

- successful claim registration with native GEN value
- successful challenge from a different account with challenge bond
- successful `WEB_TEXT` evidence submission using `https://example.com`
- successful consensus resolution from contract-side URL evidence
- expected callback failure when no callback is configured
- successful unchallenged withdrawal
- successful unchallenged cancellation
- expected invalid evidence failure
- successful unresolved timeout settlement
- reads from all view methods

Fresh full-surface StudioNet test note: the fresh deployment path reached `resolve_challenge`, then one RPC polling request to `studio.genlayer.com` timed out while waiting for the transaction receipt. The exact deployed-address StudioNet test passed afterward and is the measured write-surface proof for this submitted CA.

## Current Deployed Stats

```json
{
  "next_claim_id": "8",
  "open_claims": "4",
  "challenged_claims": "0",
  "resolved_claims": "7",
  "cancelled_claims": "2",
  "total_bonded": "7600000000000000000",
  "total_slashed": "0",
  "total_returned": "7600000000000000000",
  "total_challenger_rewards": "0",
  "balance": "0",
  "treasury": "0x9dbe27C8e1884AD3a7Be2FC606dFb40a9eEb1dfE"
}
```

Read live with `genlayer call 0xd7Ae325d6e45891AEE581a532E80757496b0109E stats`.

## Why It Is Reusable

Importers do not need to copy evidence review, source fetching, slashing, challenge, or payout logic. A registry or insurance protocol can register claims, query `claim_status` and `claim_verdict`, or receive `on_claim_resolved(...)` callbacks. The primitive is claim-generic and can support provider attestations, credential claims, reserve claims, compliance claims, safety claims, uptime claims, grant eligibility claims, and listing-quality claims.

## Honest Limit

Public URL fetching depends on source availability through GenLayer's renderer. Failed reads become `UNREADABLE` and cannot cause payout or slashing. The vault does not authenticate private, paywalled, login-gated, or cryptographically signed documents by itself; importers should write policies that define acceptable public evidence sources for their claim domain.

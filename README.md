# Bonded Claim Slashing Vault

Standalone GenLayer Intelligent Contract primitive for staking native GEN behind externally verifiable claims and slashing false claims after consensus review.

This is contract-only. No frontend belongs in this Intelligent Contract submission.

## Deployed Contract

- StudioNet contract: `0x0e02dAd35b39349F672CFBF44FF5ADE1B69b6aE6`
- Deployment tx: `0x9f9985f33acdcb6c95e4f109fea1a8b8427d7508bdf1412bb42897e6bee07b1f`
- Receipt status: `ACCEPTED`
- Deployment result: `MAJORITY_AGREE`
- Consensus: 5/5 validators agreed
- Constructor: zero treasury address was supplied, so the contract set the deployer as treasury.

This is the corrected resubmission deployment. It includes the OPEN-counter lifecycle fix. Older deployments are not the submitted contract.

## What It Does

Claimants register claims with a native GEN bond, a verification policy, a challenge window, a resolution window, a slashing percentage, and an optional callback contract. A different account can bond a challenge. Claim parties can submit bounded evidence. Validators then judge whether independently acquired evidence upholds, refutes, or cannot resolve the claim under the policy. The contract normalizes that verdict and deterministically settles funds.

This is designed as a reusable primitive for reputation systems, registries, insurance protocols, curation markets, compliance lists, agent marketplaces, and other systems that need claim truthfulness backed by slashable economic pressure.

## Contract-Side Evidence Acquisition

The hardened `resolve_challenge` flow now fetches public source material inside the nondeterministic execution path before validator adjudication:

- `WEB_TEXT`, `WEB_SCREENSHOT`, and `IMAGE_URL` evidence are treated as public URL evidence.
- During `resolve_challenge`, each public URL is read with `gl.nondet.web.render`.
- The fetched material is capped to a compact `contract_fetched_excerpt`.
- Validators receive `source_fetch_status`: `FETCHED`, `UNREADABLE`, or `NOT_REQUESTED`.
- Failed external reads become `UNREADABLE` and cannot be used as proof.
- Plain `TEXT` remains party-supplied context and is not independent source proof by itself.

This addresses the original rejection directly: the vault no longer pays or slashes from unread URL strings.

## Why GenLayer Is Used

The nondeterministic part is evidence acquisition and judgement: validators review claim text, verification policy, challenge text, and contract-fetched source content. The deterministic part is everything economic and stateful: bond accounting, challenge eligibility, evidence caps, deadline checks, verdict normalization, slashing math, refunds, rewards, and callback eligibility.

Without GenLayer, a registry admin, oracle operator, backend, or multisig must decide if a claim was false. Here the judgement is consensus-produced and the result directly gates contract state and GEN movement.

## Contract Surface

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

## Tested Results

- `genvm-lint check contracts\bonded_claim_slashing_vault.py --json`: passed, 15 methods, 8 writes, 7 views
- `genvm-lint check examples\claim_registry_consumer.py --json`: passed, 3 methods
- `pytest tests/direct/ -q`: `35 passed`
- `gltest tests/integration/test_deployed_contract_surface.py -v -s --network studionet`: `1 passed` against the corrected CA
- Live write testing against `0x0e02dAd35b39349F672CFBF44FF5ADE1B69b6aE6`: `open_claims` ended at `0` after resolution, withdrawal, cancellation, and timeout

The exact deployed-address test wrote against `0x0e02dAd35b39349F672CFBF44FF5ADE1B69b6aE6` and exercised:

- successful claim registration with native GEN value
- successful challenge from a different account with challenge bond
- successful `WEB_TEXT` evidence submission
- successful consensus resolution from contract-side URL evidence
- expected callback failure when no callback is configured
- successful unchallenged withdrawal
- successful unchallenged cancellation
- expected invalid evidence failure
- successful unresolved timeout settlement
- reads from all view methods

The fresh full-surface StudioNet test completed successfully and is the measured proof for this submitted CA.

Current deployed stats after the exact-address write test:

```json
{
  "next_claim_id": "5",
  "open_claims": "0",
  "challenged_claims": "0",
  "resolved_claims": "4",
  "cancelled_claims": "1",
  "total_bonded": "4400000000000000000",
  "total_slashed": "0",
  "total_returned": "4400000000000000000",
  "total_challenger_rewards": "0",
  "balance": "0",
  "treasury": "0x9dbe27C8e1884AD3a7Be2FC606dFb40a9eEb1dfE"
}
```

## Package

- `contracts/`: primitive source
- `examples/`: worked consumer interface example
- `tests/direct/`: adversarial direct-mode tests
- `tests/integration/`: StudioNet tests
- `docs/`: submission package
- `DECISION_RECORD.md`: idea gates and design notes

## Runbook

```powershell
genvm-lint check 'contracts\bonded_claim_slashing_vault.py' --json
genvm-lint check 'examples\claim_registry_consumer.py' --json
pytest tests/direct/ -q
gltest tests/integration/test_deployed_contract_surface.py -v -s --network studionet
```

Deploy syntax:

```powershell
genlayer.cmd deploy --contract 'contracts\bonded_claim_slashing_vault.py' --args 0x0000000000000000000000000000000000000000
```

## Limits

URL fetching is intentionally conservative: public HTTP(S) evidence must be available to GenLayer's renderer, fetched excerpts are capped, and failed reads are treated as `UNREADABLE` rather than proof. The vault does not authenticate private, paywalled, login-gated, or cryptographically signed documents by itself. Importers should write verification policies that name acceptable public source classes for their domain.

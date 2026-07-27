# Bonded Claim Slashing Vault

Standalone GenLayer Intelligent Contract primitive for staking native GEN behind externally verifiable claims and slashing false claims after consensus review.

This is contract-only. No frontend belongs in this Intelligent Contract submission.

## Deployed Contract

- StudioNet contract: `0x294F85B407df89A18ec94D6bE2ce314ce16dC606`
- Deployment tx: `0xad81446a1831fe252aac3c1db00639779566cd554ba2ee050a352e0b741c5186`
- Receipt status: `FINALIZED`
- Consensus: 5/5 validators agreed
- Constructor: zero treasury address was supplied, so the contract set the deployer as treasury.

One earlier deployment attempt used the wrong CLI argument shape and produced `0x00E6875495a0e80382a1242F47b70178298eE3a0`; that address is not found by StudioNet and is not the submitted contract.

## What It Does

Claimants register claims with a native GEN bond, a verification policy, a challenge window, a resolution window, a slashing percentage, and an optional callback contract. A different account can bond a challenge. Claim parties can submit bounded evidence. Validators then judge whether the evidence upholds, refutes, or cannot resolve the claim under the policy. The contract normalizes that verdict and deterministically settles funds.

This is designed as a reusable primitive for reputation systems, registries, insurance protocols, curation markets, compliance lists, agent marketplaces, and other systems that need claim truthfulness backed by slashable economic pressure.

## Why GenLayer Is Used

The non-deterministic part is the evidence judgement: validators review claim text, verification policy, challenge text, and submitted evidence. The deterministic part is everything economic and stateful: bond accounting, challenge eligibility, evidence caps, deadline checks, verdict normalization, slashing math, refunds, rewards, and callback eligibility.

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
- `pytest tests/direct/ -q`: `31 passed`
- `gltest tests/integration/test_full_surface_studionet.py -v -s --network studionet`: `1 passed`
- `gltest tests/integration/test_deployed_contract_surface.py -v -s --network studionet`: `1 passed`
- `genlayer.cmd schema 0x294F85B407df89A18ec94D6bE2ce314ce16dC606`: retrieved successfully
- `genlayer.cmd receipt 0xad81446a1831fe252aac3c1db00639779566cd554ba2ee050a352e0b741c5186`: finalized
- `genlayer.cmd call 0x294F85B407df89A18ec94D6bE2ce314ce16dC606 stats`: returned current deployed stats after write testing

Current deployed stats after the exact-address write test:

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
gltest tests/integration/test_full_surface_studionet.py -v -s --network studionet
gltest tests/integration/test_deployed_contract_surface.py -v -s --network studionet
```

Deploy syntax:

```powershell
genlayer.cmd deploy --contract 'contracts\bonded_claim_slashing_vault.py' --args 0x0000000000000000000000000000000000000000
```

## Limits

The current implementation stores evidence text or URIs and asks validators to judge the evidence bundle. It is already useful as a bonded claim primitive, but a later hardening pass can add contract-side web fetching/rendering per evidence kind where an importer needs stronger source acquisition guarantees.

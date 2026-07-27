# Decision Record: Bonded Claim Slashing Vault

## Chosen primitive

**Bonded Claim Slashing Vault** is a standalone GenLayer Intelligent Contract primitive where a claimant stakes native GEN behind a claim, challengers can bond a dispute, validators judge external evidence, and deterministic code releases or slashes bonds according to a bounded verdict.

Importers: reputation systems, registries, insurance pools, curation markets, grant programs, compliance registries, and agent marketplaces that need reusable economic pressure behind externally verifiable claims.

## Why this is not a thin oracle

The primitive does not return advice, summaries, or free text. It gates economic state. A claim is either upheld, refuted, inconclusive, externally failed, stale, or outside policy. The judgement is consensus-produced; the slashing/refund/reward math is deterministic.

Without GenLayer, a registry admin, oracle operator, marketplace backend, or multisig decides whether a claim survives. With GenLayer, mutually distrusting claimants, challengers, and downstream contracts can rely on a consensus verdict with funds locked in the same system.

## Differentiation from the previous escrow

Evidence-Gated Intent Escrow settles bilateral service fulfilment. This vault handles public or registry claims with adversarial challenges, claim bonds, challenge bonds, challenger rewards, and claim state that downstream contracts can query.

It is a different primitive:

- claim-first rather than task-first
- challenger-triggered rather than fulfiller-submitted settlement
- slashing/reputation oriented rather than service payout oriented
- useful for registries and insurance policies where a false claim imposes external risk

## Gates

### Counterfactual

Delete GenLayer and a central registry or claim-review backend decides whether a claim is false. Claimants and challengers must trust that party to apply evidence consistently and not suppress challenges.

### Trust problem

The claimant wants the claim accepted, a challenger may want false claims removed, and downstream contracts may rely on the claim to issue reputation, unlock access, price insurance, or include registry entries. One party may control some evidence, so consensus must judge evidence under a fixed policy.

### Judgement

The core question is semantic: does external evidence support, refute, or fail to resolve a claim under its policy? Deterministic code can enforce timing, bonds, caps, and payouts, but it cannot judge claim truth from heterogeneous evidence.

### Importability

Consumer contracts only need to open or read claims:

```python
@gl.contract_interface
class IBondedClaimVault:
    class View:
        def claim_status(self, claim_id: u256) -> str: ...
        def claim_verdict(self, claim_id: u256) -> str: ...
```

They do not copy evidence review or slashing machinery.

### Consequential state

Consensus verdicts gate staked GEN, challenger rewards, slash accounting, accepted/refuted claim state, and optional callbacks.

### Originality

This is not the supplied collision lane of source-corroboration/source-reputation oracle, and it is not page-change detection. It is an economic primitive for bonded claims and slashing.

## Non-determinism budget

Resolution uses one nondeterministic prompt over the claim, policy, challenge statement, and evidence bundle. The first implementation stores evidence text/URIs as data and mocks validator outputs in tests. A hardening pass can add one `web.get` or `web.render` branch per evidence kind without changing settlement semantics.

## Deterministic responsibilities

The contract deterministically handles:

- claim registration and claim bond accounting
- challenger bond accounting
- evidence caps
- challenge windows and resolution deadlines
- verdict normalization and malformed output handling
- slashing math
- reward/refund routing
- replay and double-settlement protection
- callback eligibility
- all view envelopes

## Verdicts

- `UPHELD`: evidence supports the claim; claimant keeps claim bond and receives challenger bond.
- `REFUTED`: evidence refutes the claim; claimant bond is slashed, challenger gets configured reward.
- `INCONCLUSIVE`: no immediate slashing; retry until deadline, then both bonds return.
- `EXTERNAL_FAILURE`: no immediate slashing; retry until deadline, then both bonds return.
- `STALE_EVIDENCE`: no immediate slashing unless policy declares stale evidence as refutation.
- `OUT_OF_SCOPE`: no immediate slashing; challenge bond can be forfeited only when deterministic policy says challenge is invalid.

## Funds

Every terminal state has a defined resting place. Funds are never implicitly stranded:

- Accepted without challenge: claimant can withdraw claim bond after expiry.
- Upheld after challenge: claimant receives claim bond plus challenger bond.
- Refuted: challenger receives configured reward from claimant bond plus their challenge bond; the remainder goes to treasury.
- Inconclusive/external failure at timeout: claimant and challenger recover their own bonds.
- Cancelled before challenge: claimant recovers claim bond.

State is written before transfers are emitted.

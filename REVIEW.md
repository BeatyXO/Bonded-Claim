# Review Response: Bonded Claim Slashing Vault

## Steward request addressed

The public lifecycle counters now remain consistent when claims leave the `OPEN` state.

### Changes made

- `register_claim` increments `open_claims` when a claim is created.
- `challenge_claim` decrements `open_claims` when the claim becomes `CHALLENGED`.
- The shared `_mark_settled` transition helper now detects an `OPEN` claim and decrements `open_claims` before recording settlement.
- Both `withdraw_unchallenged` and `cancel_unchallenged` use this shared path, so neither can settle an OPEN claim while leaving the aggregate counter inflated.
- Regression tests explicitly verify `open_claims == 0` after withdrawal and cancellation.

## Verification

- Direct suite: `35 passed`.
- GenVM lint: passed for the vault and consumer example.
- StudioNet write-surface test: `1 passed` against the matching deployment.
- Live flow covered registration, challenge, evidence, consensus resolution, withdrawal, cancellation, timeout, and final counter readback. The final `open_claims` value was `0`.

## Matching deployment

- Contract: `0x0e02dAd35b39349F672CFBF44FF5ADE1B69b6aE6`
- Deployment transaction: `0x9f9985f33acdcb6c95e4f109fea1a8b8427d7508bdf1412bb42897e6bee07b1f`
- Explorer: https://explorer-studio.genlayer.com/address/0x0e02dAd35b39349F672CFBF44FF5ADE1B69b6aE6

The deployment address, integration test, README, and submission package all match this source revision.

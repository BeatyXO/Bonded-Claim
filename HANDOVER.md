# Handover — status: DONE, corrected OPEN counter

## Reviewer feedback (Joaquin, Aug 4 2026 14:31) — resolved

> UPHELD or REFUTED can be stored with ok=false, while funds are settled from the
> verdict alone. Enforce one invariant between these fields ... then submit matching
> corrected source and deployment.

All requested work is complete:

1. **Source fix** — [contracts/bonded_claim_slashing_vault.py](contracts/bonded_claim_slashing_vault.py),
   `_normalize_resolution`: a conclusive verdict (`UPHELD`/`REFUTED`) is only kept
   conclusive when the model also reported `ok=true`; otherwise it's downgraded to
   `INCONCLUSIVE` with `ok=false`, so `resolve_challenge` never settles funds on a
   self-contradictory result.
2. **Tests** — added `test_upheld_with_ok_false_downgrades_to_inconclusive` and
   `test_refuted_with_ok_false_downgrades_to_inconclusive` in
   [tests/direct/test_bonded_claim_slashing_vault.py](tests/direct/test_bonded_claim_slashing_vault.py).
   Full direct suite: **35/35 passing**.
3. **Lint** — clean (`genvm-lint check contracts/bonded_claim_slashing_vault.py --json` → `ok:true`).
4. **Redeployed to StudioNet** with the fix:
   - New contract address: `0x0e02dAd35b39349F672CFBF44FF5ADE1B69b6aE6`
   - Deployment tx: `0x9f9985f33acdcb6c95e4f109fea1a8b8427d7508bdf1412bb42897e6bee07b1f`
   - `MAJORITY_AGREE`, 5-validator round, quorum in round 0
   - Older deployments are superseded — do not resubmit them.
5. **Full write-surface exercised on the new address** —
   [tests/integration/test_deployed_contract_surface.py](tests/integration/test_deployed_contract_surface.py)
   updated to point at the new `DEPLOYED_ADDRESS` and given a wider RPC poll interval
   (`wait_interval=8000, wait_retries=90` — StudioNet rate-limits at 30 req/min and the
   default 3000ms interval trips it across this many sequential txs). Ran green:
   `1 passed in 474.70s`.
6. **`docs/SUBMISSION_PACKAGE.md` updated**: new address/tx/votes, refreshed
   `stats()` output pulled live from chain, fix changelog note at the top.

## What's left — commit and submit

The source, tests, deployment, and documentation are complete:

```
modified:   contracts/bonded_claim_slashing_vault.py
modified:   docs/SUBMISSION_PACKAGE.md
modified:   tests/direct/test_bonded_claim_slashing_vault.py
modified:   tests/integration/test_deployed_contract_surface.py
```

Per this repo's norms: don't commit or push without the user's go-ahead, and never add
an AI/agent co-author trailer. If asked to commit, verify after with:
```bash
git log -1 --format='%B' | grep -i "co-authored\|claude\|generated with"
```
(should return nothing).

## Reference

- Deployer account: `bonded-claim-slashing-deployer` (`0x8b998319628dc04e83a3116e74394afa34aa98a3`)
- Treasury: `api-schema-sentinel-deployer` (`0x9dbe27C8e1884AD3a7Be2FC606dFb40a9eEb1dfE`)
- New deployed address: `0x0e02dAd35b39349F672CFBF44FF5ADE1B69b6aE6`
- New deployment tx: `0x9f9985f33acdcb6c95e4f109fea1a8b8427d7508bdf1412bb42897e6bee07b1f`
- Network: StudioNet, `https://studio.genlayer.com/api`, gasless

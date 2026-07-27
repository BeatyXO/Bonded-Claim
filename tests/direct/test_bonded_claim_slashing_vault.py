import json

from conftest import set_value, warp_to


CONTRACT = "contracts/bonded_claim_slashing_vault.py"
ZERO = "0x0000000000000000000000000000000000000000"
GEN = 10**18


def deploy(direct_deploy, direct_vm, treasury):
    contract = direct_deploy(CONTRACT, treasury)
    direct_vm.check_pickling = True
    warp_to(direct_vm, "2026-07-27T12:00:00Z")
    return contract


def register_default(contract, direct_vm, claimant, bond=GEN, callback=ZERO):
    direct_vm.sender = claimant
    set_value(direct_vm, bond)
    return contract.register_claim(
        "Provider alpha has maintained SOC2 Type II coverage for the current review window.",
        "Evidence must include dated audit, registry, or public attestation proof for provider alpha.",
        3600,
        7200,
        7000,
        callback,
    )


def challenge_default(contract, direct_vm, claim_id, challenger, bond=GEN // 5):
    direct_vm.sender = challenger
    set_value(direct_vm, bond)
    contract.challenge_claim(
        claim_id,
        "The provider alpha claim appears false or expired based on the latest public evidence.",
    )


def submit_default(contract, direct_vm, claim_id, sender):
    direct_vm.sender = sender
    contract.submit_evidence(
        claim_id,
        "TEXT",
        "Public registry entry says provider alpha status is current for the review window.",
        "Submitted as claim evidence.",
    )


def mock_verdict(direct_vm, verdict, ok=True, reason="mocked verdict"):
    direct_vm.clear_mocks()
    direct_vm.mock_llm(
        r".*GenLayer validator judging a bonded claim challenge.*",
        json.dumps(
            {
                "ok": ok,
                "verdict": verdict,
                "reason": reason,
                "evidence_summary": "Evidence was reviewed against the policy.",
                "weaknesses": "",
                "safe_error": "",
            }
        ),
    )


def claim(contract, claim_id):
    return json.loads(contract.get_claim(claim_id))


def test_register_claim_records_bond_and_deadline(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    rec = claim(contract, claim_id)
    assert rec["claim_bond"] == str(GEN)
    assert rec["status"] == "OPEN"
    assert rec["challenge_deadline"] == "2026-07-27T13:00:00Z"


def test_register_requires_claim_bond(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    direct_vm.sender = direct_alice
    set_value(direct_vm, 0)
    with direct_vm.expect_revert("claim bond required"):
        contract.register_claim("claim", "policy", 3600, 7200, 7000, ZERO)


def test_register_rejects_short_challenge_window(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    direct_vm.sender = direct_alice
    set_value(direct_vm, GEN)
    with direct_vm.expect_revert("challenge window too short"):
        contract.register_claim("claim", "policy", 10, 7200, 7000, ZERO)


def test_register_rejects_invalid_slash_bps(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    direct_vm.sender = direct_alice
    set_value(direct_vm, GEN)
    with direct_vm.expect_revert("invalid slash bps"):
        contract.register_claim("claim", "policy", 3600, 7200, 0, ZERO)


def test_challenge_records_challenger_and_bond(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    rec = claim(contract, claim_id)
    assert rec["status"] == "CHALLENGED"
    assert rec["challenge_bond"] == str(GEN // 5)


def test_claimant_cannot_challenge_own_claim(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    direct_vm.sender = direct_alice
    set_value(direct_vm, GEN // 5)
    with direct_vm.expect_revert("claimant cannot challenge"):
        contract.challenge_claim(claim_id, "bad claim")


def test_challenge_after_deadline_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    warp_to(direct_vm, "2026-07-27T13:00:01Z")
    direct_vm.sender = direct_bob
    set_value(direct_vm, GEN // 5)
    with direct_vm.expect_revert("challenge window passed"):
        contract.challenge_claim(claim_id, "late")


def test_challenge_at_exact_deadline_allowed(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    warp_to(direct_vm, "2026-07-27T13:00:00Z")
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    assert claim(contract, claim_id)["status"] == "CHALLENGED"


def test_party_can_submit_evidence(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_alice)
    item = json.loads(contract.get_evidence(claim_id, 0))
    assert item["kind"] == "TEXT"


def test_stranger_cannot_submit_evidence(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("only claim party can submit evidence"):
        contract.submit_evidence(claim_id, "TEXT", "evidence", "")


def test_submit_evidence_rejects_bad_kind(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("unsupported evidence kind"):
        contract.submit_evidence(claim_id, "PDF", "evidence", "")


def test_submit_evidence_cap(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    direct_vm.sender = direct_bob
    for i in range(5):
        contract.submit_evidence(claim_id, "TEXT", f"evidence {i}", "")
    with direct_vm.expect_revert("evidence cap reached"):
        contract.submit_evidence(claim_id, "TEXT", "sixth", "")


def test_resolve_upheld_pays_claimant_both_bonds(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_alice)
    mock_verdict(direct_vm, "UPHELD")
    contract.resolve_challenge(claim_id)
    rec = claim(contract, claim_id)
    assert rec["verdict"] == "UPHELD"
    assert rec["claimant_payout"] == str(GEN + GEN // 5)


def test_resolve_refuted_slashes_claimant_to_challenger_and_treasury(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_bob)
    mock_verdict(direct_vm, "REFUTED")
    contract.resolve_challenge(claim_id)
    rec = claim(contract, claim_id)
    assert rec["verdict"] == "REFUTED"
    assert rec["challenger_payout"] == str(GEN * 7000 // 10000 + GEN // 5)
    assert rec["treasury_payout"] == str(GEN * 3000 // 10000)


def test_resolve_inconclusive_does_not_settle(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_bob)
    mock_verdict(direct_vm, "INCONCLUSIVE", ok=False)
    contract.resolve_challenge(claim_id)
    rec = claim(contract, claim_id)
    assert rec["settled"] is False
    assert rec["verdict"] == "INCONCLUSIVE"


def test_external_failure_does_not_slash(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_bob)
    mock_verdict(direct_vm, "EXTERNAL_FAILURE", ok=True)
    contract.resolve_challenge(claim_id)
    rec = claim(contract, claim_id)
    assert rec["settled"] is False
    assert rec["challenger_payout"] == "0"


def test_unknown_verdict_clamped_inconclusive(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_bob)
    mock_verdict(direct_vm, "SLASH_EVERYONE", ok=True)
    contract.resolve_challenge(claim_id)
    assert claim(contract, claim_id)["verdict"] == "INCONCLUSIVE"


def test_malformed_model_output_clamped_inconclusive(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_bob)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*GenLayer validator judging a bonded claim challenge.*", "not-json")
    contract.resolve_challenge(claim_id)
    assert claim(contract, claim_id)["verdict"] == "INCONCLUSIVE"


def test_resolve_requires_challenge(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    with direct_vm.expect_revert("challenged claim required"):
        contract.resolve_challenge(claim_id)


def test_resolve_requires_evidence(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    with direct_vm.expect_revert("evidence required"):
        contract.resolve_challenge(claim_id)


def test_resolve_after_deadline_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_bob)
    warp_to(direct_vm, "2026-07-27T15:00:01Z")
    with direct_vm.expect_revert("resolution deadline passed"):
        contract.resolve_challenge(claim_id)


def test_resolve_at_exact_deadline_allowed(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_bob)
    warp_to(direct_vm, "2026-07-27T14:00:00Z")
    mock_verdict(direct_vm, "UPHELD")
    contract.resolve_challenge(claim_id)
    assert claim(contract, claim_id)["settled"] is True


def test_timeout_unresolved_returns_both_bonds(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    warp_to(direct_vm, "2026-07-27T15:00:01Z")
    contract.timeout_unresolved(claim_id)
    rec = claim(contract, claim_id)
    assert rec["settled"] is True
    assert rec["claimant_payout"] == str(GEN)
    assert rec["challenger_payout"] == str(GEN // 5)


def test_timeout_requires_deadline(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    with direct_vm.expect_revert("resolution deadline active"):
        contract.timeout_unresolved(claim_id)


def test_withdraw_unchallenged_after_window(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    warp_to(direct_vm, "2026-07-27T13:00:01Z")
    direct_vm.sender = direct_alice
    contract.withdraw_unchallenged(claim_id)
    rec = claim(contract, claim_id)
    assert rec["status"] == "EXPIRED"
    assert rec["claimant_payout"] == str(GEN)


def test_withdraw_unchallenged_requires_window_end(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("challenge window active"):
        contract.withdraw_unchallenged(claim_id)


def test_cancel_unchallenged_returns_bond(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    direct_vm.sender = direct_alice
    contract.cancel_unchallenged(claim_id)
    rec = claim(contract, claim_id)
    assert rec["status"] == "CANCELLED"
    assert rec["claimant_payout"] == str(GEN)


def test_cancel_challenged_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("only open claim can cancel"):
        contract.cancel_unchallenged(claim_id)


def test_double_settlement_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_bob)
    mock_verdict(direct_vm, "REFUTED")
    contract.resolve_challenge(claim_id)
    with direct_vm.expect_revert("challenged claim required"):
        contract.resolve_challenge(claim_id)


def test_send_callback_without_callback_fails(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_bob)
    mock_verdict(direct_vm, "UPHELD")
    contract.resolve_challenge(claim_id)
    with direct_vm.expect_revert("no callback"):
        contract.send_callback(claim_id)


def test_views_return_terms_resolution_and_stats(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm, direct_alice)
    claim_id = register_default(contract, direct_vm, direct_alice)
    challenge_default(contract, direct_vm, claim_id, direct_bob)
    submit_default(contract, direct_vm, claim_id, direct_bob)
    terms = json.loads(contract.get_claim_terms(claim_id))
    assert "SOC2" in terms["claim_text"]
    assert contract.claim_status(claim_id) == "CHALLENGED"
    assert contract.claim_verdict(claim_id) == "NONE"
    assert json.loads(contract.resolution_of(claim_id))["verdict"] == "NONE"
    stats = json.loads(contract.stats())
    assert stats["next_claim_id"] == "2"

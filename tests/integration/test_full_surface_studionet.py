import json

from gltest import get_contract_factory, get_validator_factory
from gltest.assertions import tx_execution_failed, tx_execution_succeeded


CONTRACT = "BondedClaimSlashingVault"
ZERO = "0x0000000000000000000000000000000000000000"
GEN = 10**18


def mock_context(verdict="UPHELD", ok=True, now="2026-07-27T14:00:00Z"):
    validators = get_validator_factory().batch_create_mock_validators(
        count=5,
        mock_llm_response={
            "nondet_exec_prompt": {
                "GenLayer validator judging a bonded claim challenge": json.dumps(
                    {
                        "ok": ok,
                        "verdict": verdict,
                        "reason": "mocked StudioNet claim verdict",
                        "evidence_summary": "mocked claim evidence summary",
                        "weaknesses": "",
                        "safe_error": "",
                    }
                )
            }
        },
    )
    return {"validators": [v.to_dict() for v in validators], "genvm_datetime": now}


def register_args(callback=ZERO):
    return [
        "Provider alpha has maintained SOC2 Type II coverage for the current review window.",
        "Evidence must include dated audit, registry, or public attestation proof for provider alpha.",
        3600,
        7200,
        7000,
        callback,
    ]


def challenge_args():
    return ["The provider alpha claim appears false or expired based on public evidence."]


def evidence_args(claim_id):
    return [
        claim_id,
        "TEXT",
        "Public registry entry says provider alpha status is current for the review window.",
        "StudioNet integration evidence.",
    ]


def test_full_surface_on_studionet(default_account, accounts):
    factory = get_contract_factory(CONTRACT)
    contract = factory.deploy(
        args=[default_account.address],
        account=default_account,
        transaction_context=mock_context(),
    ).connect(default_account)
    challenger_contract = contract.connect(accounts[1])

    register_tx = contract.register_claim(args=register_args()).transact(
        value=GEN, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(register_tx)

    challenge_tx = challenger_contract.challenge_claim(args=[1] + challenge_args()).transact(
        value=GEN // 5, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(challenge_tx)

    evidence_tx = contract.submit_evidence(args=evidence_args(1)).transact(
        transaction_context=mock_context()
    )
    assert tx_execution_succeeded(evidence_tx)

    resolve_tx = contract.resolve_challenge(args=[1]).transact(
        transaction_context=mock_context("UPHELD", True)
    )
    assert tx_execution_succeeded(resolve_tx)

    callback_tx = contract.send_callback(args=[1]).transact(
        transaction_context=mock_context()
    )
    assert tx_execution_failed(callback_tx)

    claim2_tx = contract.register_claim(args=register_args()).transact(
        value=GEN, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(claim2_tx)
    withdraw_tx = contract.withdraw_unchallenged(args=[2]).transact(
        transaction_context=mock_context(now="2026-07-27T15:00:01Z")
    )
    assert tx_execution_succeeded(withdraw_tx)

    claim3_tx = contract.register_claim(args=register_args()).transact(
        value=GEN, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(claim3_tx)
    cancel_tx = contract.cancel_unchallenged(args=[3]).transact(
        transaction_context=mock_context()
    )
    assert tx_execution_succeeded(cancel_tx)

    claim4_tx = contract.register_claim(args=register_args()).transact(
        value=GEN, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(claim4_tx)
    challenge4_tx = challenger_contract.challenge_claim(args=[4] + challenge_args()).transact(
        value=GEN // 5, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(challenge4_tx)

    bad_evidence_tx = contract.submit_evidence(args=[4, "BAD", "{}", ""]).transact(
        transaction_context=mock_context()
    )
    assert tx_execution_failed(bad_evidence_tx)

    timeout_tx = contract.timeout_unresolved(args=[4]).transact(
        transaction_context=mock_context(now="2026-07-27T18:00:01Z")
    )
    assert tx_execution_succeeded(timeout_tx)

    assert contract.claim_status(args=[1]).call() == "RESOLVED"
    assert contract.claim_verdict(args=[1]).call() == "UPHELD"
    assert json.loads(contract.get_evidence(args=[1, 0]).call())["kind"] == "TEXT"
    assert "SOC2" in json.loads(contract.get_claim_terms(args=[1]).call())["claim_text"]
    assert json.loads(contract.resolution_of(args=[1]).call())["verdict"] == "UPHELD"
    stats = json.loads(contract.stats(args=[]).call())
    assert int(stats["next_claim_id"]) >= 5

import json

from gltest import get_contract_factory, get_validator_factory
from gltest.assertions import tx_execution_failed, tx_execution_succeeded


CONTRACT = "BondedClaimSlashingVault"
DEPLOYED_ADDRESS = "0x0e02dAd35b39349F672CFBF44FF5ADE1B69b6aE6"
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
                        "reason": "mocked deployed-CA verdict from contract-fetched URL evidence",
                        "evidence_summary": "mocked deployed-CA fetched evidence summary",
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
        "The public page at example.com identifies itself as Example Domain.",
        "Evidence must be fetched contract-side from a public URL and judged from the fetched source content.",
        3600,
        7200,
        7000,
        callback,
    ]


def challenge_args():
    return ["The page may not identify itself as Example Domain unless the public URL is fetched."]


def evidence_args(claim_id):
    return [
        claim_id,
        "WEB_TEXT",
        "https://example.com",
        "Deployed CA integration URL evidence.",
    ]


def claim_base(contract):
    return int(json.loads(contract.stats(args=[]).call())["next_claim_id"])


def test_deployed_contract_write_surface(default_account, accounts):
    factory = get_contract_factory(CONTRACT)
    contract = factory.build_contract(
        contract_address=DEPLOYED_ADDRESS,
        account=default_account,
    ).connect(default_account)
    challenger_contract = contract.connect(accounts[1])

    base = claim_base(contract)

    register_tx = contract.register_claim(args=register_args()).transact(
        value=GEN, wait_interval=8000, wait_retries=90, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(register_tx)

    challenge_tx = challenger_contract.challenge_claim(args=[base] + challenge_args()).transact(
        value=GEN // 5, wait_interval=8000, wait_retries=90, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(challenge_tx)

    evidence_tx = contract.submit_evidence(args=evidence_args(base)).transact(
        wait_interval=8000, wait_retries=90, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(evidence_tx)

    resolve_tx = contract.resolve_challenge(args=[base]).transact(
        wait_interval=8000, wait_retries=90, transaction_context=mock_context("UPHELD", True)
    )
    assert tx_execution_succeeded(resolve_tx)

    callback_tx = contract.send_callback(args=[base]).transact(
        wait_interval=8000, wait_retries=90, transaction_context=mock_context()
    )
    assert tx_execution_failed(callback_tx)

    withdraw_id = base + 1
    withdraw_claim_tx = contract.register_claim(args=register_args()).transact(
        value=GEN, wait_interval=8000, wait_retries=90, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(withdraw_claim_tx)
    withdraw_tx = contract.withdraw_unchallenged(args=[withdraw_id]).transact(
        wait_interval=8000, wait_retries=90, transaction_context=mock_context(now="2026-07-27T15:00:01Z")
    )
    assert tx_execution_succeeded(withdraw_tx)

    cancel_id = base + 2
    cancel_claim_tx = contract.register_claim(args=register_args()).transact(
        value=GEN, wait_interval=8000, wait_retries=90, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(cancel_claim_tx)
    cancel_tx = contract.cancel_unchallenged(args=[cancel_id]).transact(
        wait_interval=8000, wait_retries=90, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(cancel_tx)

    timeout_id = base + 3
    timeout_claim_tx = contract.register_claim(args=register_args()).transact(
        value=GEN, wait_interval=8000, wait_retries=90, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(timeout_claim_tx)
    timeout_challenge_tx = challenger_contract.challenge_claim(args=[timeout_id] + challenge_args()).transact(
        value=GEN // 5, wait_interval=8000, wait_retries=90, transaction_context=mock_context()
    )
    assert tx_execution_succeeded(timeout_challenge_tx)

    bad_evidence_tx = contract.submit_evidence(args=[timeout_id, "BAD", "{}", ""]).transact(
        wait_interval=8000, wait_retries=90, transaction_context=mock_context()
    )
    assert tx_execution_failed(bad_evidence_tx)

    timeout_tx = contract.timeout_unresolved(args=[timeout_id]).transact(
        wait_interval=8000, wait_retries=90, transaction_context=mock_context(now="2026-07-27T18:00:01Z")
    )
    assert tx_execution_succeeded(timeout_tx)

    assert contract.claim_status(args=[base]).call() == "RESOLVED"
    assert contract.claim_verdict(args=[base]).call() == "UPHELD"
    assert json.loads(contract.get_evidence(args=[base, 0]).call())["kind"] == "WEB_TEXT"
    assert "Example Domain" in json.loads(contract.get_claim_terms(args=[base]).call())["claim_text"]
    assert json.loads(contract.resolution_of(args=[base]).call())["verdict"] == "UPHELD"
    stats = json.loads(contract.stats(args=[]).call())
    assert int(stats["next_claim_id"]) >= base + 4
    assert stats["open_claims"] == "0"

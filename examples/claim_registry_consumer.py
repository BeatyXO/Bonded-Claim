# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json


@gl.contract_interface
class IBondedClaimVault:
    class View:
        def claim_status(self, claim_id: u256) -> str:
            pass

        def claim_verdict(self, claim_id: u256) -> str:
            pass

    class Write:
        pass


class ClaimRegistryConsumer(gl.Contract):
    vault: Address
    accepted_count: u256
    refuted_count: u256
    last_claim_id: u256
    last_verdict: str
    accepted: TreeMap[u256, bool]

    def __init__(self, vault: Address) -> None:
        self.vault = Address(vault)
        self.accepted_count = u256(0)
        self.refuted_count = u256(0)
        self.last_claim_id = u256(0)
        self.last_verdict = ""
        self.accepted = TreeMap[u256, bool]()

    @gl.public.write
    def on_claim_resolved(
        self,
        claim_id: u256,
        claimant: Address,
        challenger: Address,
        verdict: str,
        claimant_payout: u256,
        challenger_payout: u256,
    ) -> None:
        if gl.message.sender_address != self.vault:
            raise gl.vm.UserError("EXPECTED: only vault callback")
        if claim_id in self.accepted:
            raise gl.vm.UserError("EXPECTED: duplicate callback")
        is_accepted = verdict == "UPHELD"
        self.accepted[claim_id] = is_accepted
        self.last_claim_id = claim_id
        self.last_verdict = verdict
        if is_accepted:
            self.accepted_count = self.accepted_count + u256(1)
        else:
            self.refuted_count = self.refuted_count + u256(1)

    @gl.public.view
    def summary(self) -> str:
        return json.dumps(
            {
                "vault": str(self.vault),
                "accepted_count": str(self.accepted_count),
                "refuted_count": str(self.refuted_count),
                "last_claim_id": str(self.last_claim_id),
                "last_verdict": self.last_verdict,
            }
        )

    @gl.public.view
    def is_accepted(self, claim_id: u256) -> bool:
        if claim_id not in self.accepted:
            return False
        return self.accepted[claim_id]

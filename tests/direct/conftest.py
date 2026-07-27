import atexit
import os
import sys

import pytest


_LEAKED_TEMP_FILES = []


def pytest_configure(config):
    if os.name != "nt":
        return
    try:
        import gltest.direct.loader as loader
    except ImportError:
        return

    def tolerant_inject_message_to_fd0(vm):
        import tempfile

        try:
            from genlayer.py import calldata
            from genlayer.py.types import Address
        except ImportError:
            return

        sender_addr = vm.sender
        if isinstance(sender_addr, bytes):
            sender_addr = Address(sender_addr)
        contract_addr = vm._contract_address
        if isinstance(contract_addr, bytes):
            contract_addr = Address(contract_addr)
        origin_addr = vm.origin
        if isinstance(origin_addr, bytes):
            origin_addr = Address(origin_addr)

        message_data = {
            "contract_address": contract_addr,
            "sender_address": sender_addr,
            "origin_address": origin_addr,
            "stack": [],
            "value": vm._value,
            "datetime": vm._datetime,
            "is_init": False,
            "chain_id": vm._chain_id,
            "entry_kind": 0,
            "entry_data": b"",
            "entry_stage_data": None,
        }
        encoded = calldata.encode(message_data)
        fd, path = tempfile.mkstemp()
        try:
            os.write(fd, encoded)
            os.lseek(fd, 0, os.SEEK_SET)
            vm._original_stdin_fd = os.dup(0)
            os.dup2(fd, 0)
        finally:
            os.close(fd)
            try:
                os.unlink(path)
            except PermissionError:
                _LEAKED_TEMP_FILES.append(path)

    loader._inject_message_to_fd0 = tolerant_inject_message_to_fd0


@atexit.register
def cleanup_leaked_temp_files():
    for path in _LEAKED_TEMP_FILES:
        try:
            os.unlink(path)
        except OSError:
            pass


@pytest.fixture(autouse=True)
def reset_known_contract():
    yield
    gl = sys.modules.get("genlayer.gl")
    if gl is not None:
        known = getattr(gl, "genvm_contracts", None)
        if known is not None and hasattr(known, "__known_contract__"):
            known.__known_contract__ = None


def warp_to(direct_vm, iso: str) -> None:
    direct_vm.warp(iso)
    gl = sys.modules.get("genlayer.gl")
    if gl is None:
        return
    raw = getattr(gl, "message_raw", None)
    if isinstance(raw, dict):
        raw["datetime"] = iso
    nested = getattr(getattr(gl, "message", None), "raw", None)
    if isinstance(nested, dict):
        nested["datetime"] = iso


def set_value(direct_vm, amount: int) -> None:
    direct_vm.value = amount

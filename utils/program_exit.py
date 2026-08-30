from __future__ import annotations

import builtins
from typing import Callable


_ORIGINAL_INPUT: Callable[[str], str] = builtins.input
_INSTALLED = False


def _exit_aware_input(prompt: str = "") -> str:
    """
    ShopGraph-wide input wrapper.

    Every interactive prompt accepts:
        -1
    to immediately exit the entire program.

    The hint is appended to the prompt automatically so individual modules do
    not need duplicate exit-handling code.
    """
    if "-1" not in prompt:
        prompt = f"{prompt.rstrip()} [-1 = Exit ShopGraph] "

    value = _ORIGINAL_INPUT(prompt)

    if value.strip() == "-1":
        raise SystemExit

    return value


def install_global_exit_option() -> None:
    """Install the ShopGraph-wide -1 exit option exactly once."""
    global _INSTALLED

    if _INSTALLED:
        return

    builtins.input = _exit_aware_input
    _INSTALLED = True

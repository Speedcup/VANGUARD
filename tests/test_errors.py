from __future__ import annotations

import logging
from types import ModuleType, SimpleNamespace

import pytest

from tests.support import import_module_with_stubs, make_module


class _Response:
    def __init__(self, done: bool = False) -> None:
        self._done = done
        self.sent: list[tuple[str, bool]] = []

    def is_done(self) -> bool:
        return self._done

    async def send_message(self, message: str, *, ephemeral: bool = False) -> None:
        self.sent.append((message, ephemeral))


class _Followup:
    def __init__(self) -> None:
        self.sent: list[tuple[str, bool]] = []

    async def send(self, message: str, *, ephemeral: bool = False) -> None:
        self.sent.append((message, ephemeral))


class _Interaction:
    def __init__(self, *, done: bool = False, command_name: str = "forms") -> None:
        self.response = _Response(done)
        self.followup = _Followup()
        self.command = SimpleNamespace(qualified_name=command_name)


def _import_errors_module() -> ModuleType:
    class CheckFailure(Exception):
        pass

    class AppCommandError(Exception):
        pass

    class CommandOnCooldown(AppCommandError):
        def __init__(self, retry_after: float) -> None:
            super().__init__("cooldown")
            self.retry_after = retry_after

    class Forbidden(AppCommandError):
        pass

    class HTTPException(AppCommandError):
        pass

    discord = make_module("discord", Interaction=_Interaction, app_commands=None)
    discord.Forbidden = Forbidden  # type: ignore[attr-defined]
    discord.HTTPException = HTTPException  # type: ignore[attr-defined]
    app_commands = make_module(
        "discord.app_commands",
        AppCommandError=AppCommandError,
        CheckFailure=CheckFailure,
        CommandOnCooldown=CommandOnCooldown,
    )
    discord.app_commands = app_commands  # type: ignore[attr-defined]

    utils_checks = make_module("utils.checks", NotStaff=type("NotStaff", (CheckFailure,), {}))

    return import_module_with_stubs(
        "utils.errors",
        {
            "discord": discord,
            "discord.app_commands": app_commands,
            "utils.checks": utils_checks,
        },
    )


ERRORS = _import_errors_module()


def test_error_log_generates_memorable_code_and_prefixes_logs(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("test.errors")
    error_log = ERRORS.ErrorLog(logger)
    code = error_log.make_code(ValueError("boom"))

    assert code == "panini"
    assert error_log.make_code(ERRORS.NotStaff("nope")) == "sushi"
    assert error_log.make_code(ERRORS.app_commands.CommandOnCooldown(10)) == "pizza"
    assert error_log.make_code(ERRORS.app_commands.CheckFailure("bad")) == "taco"
    assert error_log.make_code(ERRORS.discord.Forbidden("nope")) == "soup"
    assert error_log.make_code(ERRORS.discord.HTTPException("oops")) == "waffle"

    with caplog.at_level(logging.ERROR, logger="test.errors"):
        error_log.log_error(ValueError("boom"), "Unhandled error in command %r: %s", "forms", "boom")

    assert "[panini] Unhandled error in command 'forms': boom" in caplog.text


@pytest.mark.asyncio
async def test_generic_app_command_error_includes_code_in_response_and_log(caplog: pytest.LogCaptureFixture) -> None:
    interaction = _Interaction(done=False, command_name="forms suggest")

    class WrapperError(ERRORS.app_commands.AppCommandError):
        def __init__(self, original: Exception) -> None:
            super().__init__("wrapper")
            self.original = original

    error = WrapperError(ValueError("bad tuna"))
    expected_code = ERRORS.ErrorLog().make_code(error.original)

    with caplog.at_level(logging.ERROR, logger="vanguard.errors"):
        await ERRORS.on_app_command_error(interaction, error)

    assert interaction.response.sent == [
        (
            f"⚠️ Something went wrong while running that command. "
            f"The error has been logged. Error code: `{expected_code}`.",
            True,
        )
    ]
    assert interaction.followup.sent == []
    assert any(record.message.startswith(f"[{expected_code}]") for record in caplog.records)
    assert "Unhandled error in command 'forms suggest': bad tuna" in caplog.text

"""Tools primitive — tool system with ABC interface and built-in tools."""

from __future__ import annotations

import os

from openjarvis.tools._stubs import BaseTool, ToolExecutor, ToolSpec

# Tools that read/write the local filesystem, run shell commands, or touch a
# local git repo or database — meaningful on a machine you own (the desktop
# app, a local `jarvis serve`), not on a shared, ephemeral cloud container
# nobody but you should be able to run commands on. Opt-in only: unless one of
# the env vars below is set, every tool below still registers exactly as
# before (see tests/tools/test_tool_registration.py, which pins that).
_CLOUD_PROFILE_DISABLED = frozenset(
    {
        "file_read",
        "file_write",
        "apply_patch",
        "git_tool",
        "shell_exec",
        "docker_shell_exec",
        "code_interpreter",
        "code_interpreter_docker",
        "repl",
        "db_query",
        "apple_calendar",
    }
)


def _disabled_tools() -> "frozenset[str]":
    """Tool module names to skip importing (so they never register).

    Driven by two env vars, both optional and both unset by default:
    - ``OPENJARVIS_PROFILE=cloud`` — a ready-made denylist for a public web
      deployment (see docs/deployment/render.md). Everything else (memory,
      knowledge base, images, weather, search, calculator, ...) still loads.
    - ``OPENJARVIS_DISABLED_TOOLS`` — comma-separated module names, for
      further customizing either profile.
    """
    disabled: set = set()
    if os.environ.get("OPENJARVIS_PROFILE", "").strip().lower() == "cloud":
        disabled |= _CLOUD_PROFILE_DISABLED
    explicit = os.environ.get("OPENJARVIS_DISABLED_TOOLS", "")
    disabled |= {name.strip() for name in explicit.split(",") if name.strip()}
    return frozenset(disabled)


_DISABLED = _disabled_tools()


def _load(module_name: str) -> None:
    """Import one built-in tool module to trigger its @ToolRegistry.register()
    decorator(s), unless it's in the disabled set. Wrapped in try/except so
    the package loads even before individual tool modules exist yet, exactly
    as the previous per-module try/except blocks did.
    """
    if module_name in _DISABLED:
        return
    try:
        __import__(f"openjarvis.tools.{module_name}")
    except ImportError:
        pass


_load("calculator")
_load("think")
_load("retrieval")
_load("llm_tool")
_load("file_read")
_load("web_search")
_load("weather")
_load("code_interpreter")
_load("code_interpreter_docker")
_load("repl")
_load("storage_tools")
_load("mcp_adapter")
_load("channel_tools")
_load("http_request")
_load("docker_shell_exec")
_load("shell_exec")
_load("memory_manage")
_load("user_profile_manage")
_load("skill_manage")
_load("file_write")
_load("apply_patch")
_load("git_tool")
_load("db_query")
_load("pdf_tool")
_load("image_tool")
_load("audio_tool")
_load("knowledge_tools")
_load("text_to_speech")
_load("digest_collect")
_load("scan_chunks")
_load("knowledge_sql")
_load("apple_calendar")

__all__ = ["BaseTool", "ToolExecutor", "ToolSpec"]

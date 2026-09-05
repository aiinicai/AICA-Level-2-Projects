"""One ephemeral official Codex SDK thread and one turn per validation run."""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

from services.codex_result import RESULT_SCHEMA, parse_result


def _sanitized_codex_env(codex_home: Path) -> Dict[str, str]:
    overrides = {"CODEX_HOME": str(codex_home)}
    secret_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "DATABASE_URL")
    for name in os.environ:
        if any(marker in name.upper() for marker in secret_markers):
            overrides[name] = ""
    return overrides


def execute_codex_validation(
    workspace: str,
    prompt: str,
    model: str,
    effort: str,
    encrypted_auth_blob: str,
) -> Dict[str, Any]:
    from openai_codex import ApprovalMode, Codex, CodexConfig, Sandbox, __version__
    from services.credential_vault import decrypt_secret, encrypt_secret

    # Credentials must live outside the inspected workspace so the agent cannot
    # read its own tenant authentication material.
    codex_home = Path(tempfile.mkdtemp(prefix="taskchecker-codex-auth-"))
    codex_home.chmod(0o700)
    (codex_home / "auth.json").write_bytes(decrypt_secret(encrypted_auth_blob))

    try:
        with Codex(CodexConfig(env=_sanitized_codex_env(codex_home))) as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                config={
                    "sandbox_workspace_write": {"network_access": True},
                    "web_search": "live",
                },
                cwd=str(Path(workspace).resolve()),
                ephemeral=True,
                model=model,
                sandbox=Sandbox.workspace_write,
            )
            result = thread.run(prompt, effort=effort, output_schema=RESULT_SCHEMA)
            if not result.final_response:
                raise RuntimeError("Codex completed without a final response")
            parsed = parse_result(result.final_response)
            usage = None
            if result.usage is not None:
                usage = result.usage.model_dump(mode="json") if hasattr(result.usage, "model_dump") else vars(result.usage)
            return {
                "result": parsed,
                "thread_id": getattr(thread, "id", None),
                "turn_id": result.id,
                "usage": usage,
                "sdk_version": __version__,
                "updated_encrypted_auth_blob": encrypt_secret((codex_home / "auth.json").read_bytes()),
            }
    finally:
        shutil.rmtree(codex_home, ignore_errors=True)

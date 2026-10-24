#!/usr/bin/env python3
"""Resolve the OpenAI-compatible W&B TraceServer proxy for nested model calls.

Single source of truth for in-sandbox helpers that must reach the scoped W&B
LLM proxy instead of public OpenAI. Stdlib only so it can run inside the agent
sandbox.

The proxy path mirrors the host-side sandbox env setup that already injects
`OPENAI_BASE_URL`. Ambient calls prefer that verified route. Explicit target
scopes are derived from `WF_TRACE_SERVER_URL` instead. Resolution fails closed
so a sandbox that maps the W&B key into the OpenAI key slot never silently calls
the public OpenAI endpoint.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote, urlparse

if TYPE_CHECKING:
    from collections.abc import Mapping

# Keep in sync with the host-side env setup. The same template lives in
# `environments/wb_environment/environment.py` and WBAF's Modal sandbox setup.
# `test_llm_proxy.py` asserts this string so drift is caught.
LLM_PROXY_OPENAI_PATH = "/llm_proxy/scoped/{entity}/{project}/proxy/api.openai.com/v1/"
_PUBLIC_OPENAI_ROOT_HOST = "openai.com"
_PUBLIC_OPENAI_HOST_SUFFIX = ".openai.com"
_ALLOWED_BASE_URL_SCHEMES = {"http", "https"}
_SCOPED_PROXY_PATH = re.compile(
    r"(?:^|/)llm_proxy/scoped/([^/]+)/([^/]+)/"
    r"proxy/api\.openai\.com/v1/?$"
)


class ProxyResolutionError(RuntimeError):
    """Raised when no OpenAI-compatible proxy base URL can be resolved."""


def _env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def _proxy_scope(path: str) -> tuple[str, str] | None:
    match = _SCOPED_PROXY_PATH.search(path)
    if match is None:
        return None
    return unquote(match.group(1)), unquote(match.group(2))


def _validate_http_url(url: str, *, label: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme not in _ALLOWED_BASE_URL_SCHEMES
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ProxyResolutionError(f"{label} must be an absolute HTTP(S) URL")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ProxyResolutionError(f"{label} has an invalid port") from exc


def _validate_proxy_base_url(
    base_url: str,
    *,
    expected_scope: tuple[str, str] | None = None,
) -> str:
    parsed = urlparse(base_url)
    _validate_http_url(base_url, label="OpenAI-compatible proxy base URL")
    if parsed.params or parsed.query or parsed.fragment:
        raise ProxyResolutionError(
            "OpenAI-compatible proxy base URL must be an absolute HTTP(S) URL"
        )

    host = parsed.hostname.lower()
    if host == _PUBLIC_OPENAI_ROOT_HOST or host.endswith(_PUBLIC_OPENAI_HOST_SUFFIX):
        raise ProxyResolutionError(
            "OpenAI-compatible proxy base URL points to public OpenAI; configure "
            "the W&B TraceServer proxy instead"
        )
    scope = _proxy_scope(parsed.path)
    if scope is None:
        raise ProxyResolutionError(
            "OpenAI-compatible base URL is not a scoped W&B TraceServer LLM proxy route"
        )
    if expected_scope is not None and scope != expected_scope:
        raise ProxyResolutionError(
            "OpenAI-compatible proxy scope does not match the requested "
            f"{expected_scope[0]}/{expected_scope[1]} project"
        )

    return base_url.rstrip("/")


def _scoped_proxy_base_url(*, trace_server_url: str, entity: str, project: str) -> str:
    _validate_http_url(trace_server_url, label="WF_TRACE_SERVER_URL")
    proxy_path = LLM_PROXY_OPENAI_PATH.format(
        entity=quote(entity, safe=""),
        project=quote(project, safe=""),
    )
    return _validate_proxy_base_url(
        trace_server_url.rstrip("/") + proxy_path,
        expected_scope=(entity, project),
    )


def resolve_openai_base_url(
    env: Mapping[str, str] | None = None,
    *,
    target_entity: str | None = None,
    target_project: str | None = None,
) -> str:
    """Return the OpenAI-compatible base URL, never the public OpenAI fallback.

    Resolution order:
    1. An explicit target scope derived from `WF_TRACE_SERVER_URL`. This never
       reuses an injected URL for the current project.
    2. A verified `OPENAI_BASE_URL` / `OPENAI_API_BASE` for the current scope.
    3. The current scoped W&B TraceServer proxy derived from `WF_TRACE_SERVER_URL`,
       `WANDB_ENTITY`, and `WANDB_PROJECT`.

    Raises:
        ProxyResolutionError: if neither path can produce a base URL.
    """
    source = _env(env)
    if (target_entity is None) != (target_project is None):
        raise ProxyResolutionError(
            "target_entity and target_project must be provided together"
        )

    if target_entity is not None and target_project is not None:
        entity = target_entity.strip()
        project = target_project.strip()
        if not entity or not project:
            raise ProxyResolutionError(
                "target_entity and target_project must both be non-empty"
            )
        trace_server_url = source.get("WF_TRACE_SERVER_URL", "").strip()
        if not trace_server_url:
            raise ProxyResolutionError(
                "target-scoped W&B TraceServer proxy unavailable: "
                "WF_TRACE_SERVER_URL is not set"
            )
        return _scoped_proxy_base_url(
            trace_server_url=trace_server_url,
            entity=entity,
            project=project,
        )

    explicit = (
        source.get("OPENAI_BASE_URL") or source.get("OPENAI_API_BASE") or ""
    ).strip()
    if explicit:
        _validate_proxy_base_url(explicit)
        trace_server_url = source.get("WF_TRACE_SERVER_URL", "").strip()
        entity = source.get("WANDB_ENTITY", "").strip()
        project = source.get("WANDB_PROJECT", "").strip()
        if not trace_server_url or not entity or not project:
            raise ProxyResolutionError(
                "injected proxy route cannot be verified: provide "
                "WF_TRACE_SERVER_URL, WANDB_ENTITY, and WANDB_PROJECT"
            )
        expected = _scoped_proxy_base_url(
            trace_server_url=trace_server_url,
            entity=entity,
            project=project,
        )
        if explicit.rstrip("/") != expected:
            raise ProxyResolutionError(
                "injected proxy route does not match the route derived from "
                "WF_TRACE_SERVER_URL, WANDB_ENTITY, and WANDB_PROJECT"
            )
        return expected

    trace_server_url = source.get("WF_TRACE_SERVER_URL", "").strip()
    entity = source.get("WANDB_ENTITY", "").strip()
    project = source.get("WANDB_PROJECT", "").strip()
    if trace_server_url and entity and project:
        return _scoped_proxy_base_url(
            trace_server_url=trace_server_url,
            entity=entity,
            project=project,
        ).rstrip("/")

    raise ProxyResolutionError(
        "verified W&B TraceServer LLM proxy unavailable: set a scoped "
        "OPENAI_BASE_URL or provide WF_TRACE_SERVER_URL, WANDB_ENTITY, and "
        "WANDB_PROJECT"
    )


def resolve_responses_url(
    env: Mapping[str, str] | None = None,
    *,
    target_entity: str | None = None,
    target_project: str | None = None,
) -> str:
    """Return the `/responses` endpoint on the resolved proxy base URL."""
    return (
        resolve_openai_base_url(
            env,
            target_entity=target_entity,
            target_project=target_project,
        ).rstrip("/")
        + "/responses"
    )


def resolve_openai_api_key(env: Mapping[str, str] | None = None) -> str:
    """Return the OpenAI-compatible API key, raising if it is unset."""
    key = (_env(env).get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise ProxyResolutionError("OPENAI_API_KEY is not set")
    return key


def base_url_host(
    env: Mapping[str, str] | None = None,
    *,
    target_entity: str | None = None,
    target_project: str | None = None,
) -> str:
    """Return the hostname of the resolved base URL for trace auditing."""
    return (
        urlparse(
            resolve_openai_base_url(
                env,
                target_entity=target_entity,
                target_project=target_project,
            )
        ).hostname
        or ""
    )

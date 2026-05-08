"""Primary FastAPI integration surface."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, cast

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from ghappkit_client.auth import load_private_key_pem
from ghappkit_client.client import DefaultGitHubClient, GitHubClient
from ghappkit_client.errors import GitHubApiError
from ghappkit_client.token_provider import InstallationTokenProvider

from ghappkit.context import (
    BoundLogger,
    WebhookContext,
    build_payload_model,
    extract_installation_id,
    extract_repository_ref,
    extract_sender_ref,
)
from ghappkit.delivery_logging import delivery_logger
from ghappkit.exceptions import (
    HandlerError,
    PayloadParseError,
    WebhookHeaderError,
    WebhookSignatureError,
)
from ghappkit.execution import (
    DeliveryExecutor,
    FastAPIBackgroundExecutor,
    InlineExecutor,
    NoopExecutor,
)
from ghappkit.parsing import (
    GitHubDeliveryHeaders,
    parse_github_delivery_headers,
    parse_json_payload,
    qualified_event_name,
)
from ghappkit.repo_config import RepoConfigLoader
from ghappkit.routing import EventRegistry, Handler
from ghappkit.security import verify_github_signature
from ghappkit.settings import GitHubAppSettings
from ghappkit.stub_github import MissingInstallationGitHubClient


class GitHubApp:
    """FastAPI-native GitHub App registry."""

    def __init__(
        self,
        *,
        settings: GitHubAppSettings,
        executor: DeliveryExecutor | None = None,
        http_client: httpx.AsyncClient | None = None,
        token_provider: InstallationTokenProvider | None = None,
        config_ttl_seconds: float = 0,
        use_background_tasks: bool = True,
        github_client_factory: Callable[[int | None], Awaitable[Any]] | None = None,
    ) -> None:
        self.settings = settings
        self._executor_override = executor
        self._use_background = use_background_tasks
        self._registry = EventRegistry()
        self._http_client = http_client or httpx.AsyncClient()
        self._owns_http_client = http_client is None
        self._token_provider = token_provider or self._maybe_build_token_provider()
        self._config_loader = RepoConfigLoader(settings, ttl_seconds=config_ttl_seconds)
        self._client_factory = github_client_factory

    def _maybe_build_token_provider(self) -> InstallationTokenProvider | None:
        try:
            key = (
                self.settings.private_key.get_secret_value() if self.settings.private_key else None
            )
            pem = load_private_key_pem(
                secret_pem=key,
                path=self.settings.private_key_path,
            )
        except ValueError:
            return None
        return InstallationTokenProvider(
            app_id=self.settings.app_id,
            private_key_pem=pem,
            api_base_url=str(self.settings.github_api_url),
            http_client=self._http_client,
        )

    def on(self, qualified_names: str | Sequence[str]) -> Callable[[Handler], Handler]:
        """Register handler for specific qualified events."""

        def decorator(handler: Handler) -> Handler:
            self._registry.add(qualified_names, handler)
            return handler

        return decorator

    def on_any(self) -> Callable[[Handler], Handler]:
        """Register catch-all handler."""

        def decorator(handler: Handler) -> Handler:
            self._registry.add_any(handler)
            return handler

        return decorator

    def on_error(self) -> Callable[[Handler], Handler]:
        """Register error hook."""

        def decorator(handler: Handler) -> Handler:
            self._registry.add_error(handler)
            return handler

        return decorator

    def router(self) -> APIRouter:
        """FastAPI router exposing the webhook endpoint."""
        router = APIRouter()

        @router.post(self.settings.webhook_path)
        async def github_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
            body = await request.body()
            executor = self._select_executor(background_tasks)
            try:
                return await self._process_delivery(
                    request=request,
                    body=body,
                    executor=executor,
                    verify_signature=self.settings.require_signature,
                    header_map=dict(request.headers),
                )
            except WebhookSignatureError as exc:
                raise HTTPException(status_code=401, detail="invalid webhook signature") from exc
            except (WebhookHeaderError, PayloadParseError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        return router

    def _select_executor(self, background_tasks: BackgroundTasks) -> DeliveryExecutor:
        if self._executor_override is not None:
            return self._executor_override
        if self._use_background:
            return FastAPIBackgroundExecutor(background_tasks)
        return InlineExecutor()

    async def _process_delivery(
        self,
        *,
        request: Request | None,
        body: bytes,
        executor: DeliveryExecutor,
        verify_signature: bool,
        header_map: Mapping[str, str],
    ) -> Response:
        headers = parse_github_delivery_headers(header_map)
        if verify_signature:
            secret = self.settings.webhook_secret.get_secret_value()
            verify_github_signature(
                secret=secret,
                body=body,
                signature_header=headers.signature_256,
            )
        return await self._dispatch_handlers(request, headers, body, executor)

    async def _dispatch_handlers(
        self,
        request: Request | None,
        headers: GitHubDeliveryHeaders,
        body: bytes,
        executor: DeliveryExecutor,
    ) -> Response:
        payload = parse_json_payload(body)
        qualified = qualified_event_name(headers.event, payload)
        handlers = self._registry.handlers_for(qualified)

        if isinstance(executor, NoopExecutor):
            return Response(status_code=202)
        if not handlers:
            return Response(status_code=202)

        async def task() -> None:
            await self._invoke_handlers(request, headers, payload, qualified, handlers)

        try:
            await executor.enqueue(task)
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail="failed to schedule webhook handlers"
            ) from exc

        return Response(status_code=202)

    async def dispatch_for_tests(
        self,
        *,
        headers: Mapping[str, str],
        body: bytes,
        request: Request | None = None,
        executor: DeliveryExecutor | None = None,
    ) -> Response:
        """Simulate a webhook delivery without signature verification."""
        chosen = executor or InlineExecutor()
        hdrs = parse_github_delivery_headers(headers)
        return await self._dispatch_handlers(request, hdrs, body, chosen)

    async def _invoke_handlers(
        self,
        request: Request | None,
        headers: GitHubDeliveryHeaders,
        payload: dict[str, Any],
        qualified_event: str,
        handlers: Sequence[Handler],
    ) -> None:
        installation_id = extract_installation_id(payload)
        github_client = await self._create_github_client(installation_id)
        structured = delivery_logger(
            logging.getLogger("ghappkit"),
            delivery_id=headers.delivery_id,
            qualified_event=qualified_event,
            installation_id=installation_id,
            repository=self._repo_slug(payload),
            sender=self._sender_login(payload),
        )
        bound = BoundLogger(structured.logger, structured.extra)
        typed_payload = build_payload_model(qualified_event, payload)
        ctx = WebhookContext(
            delivery_id=headers.delivery_id,
            event=headers.event,
            action=payload["action"] if isinstance(payload.get("action"), str) else None,
            payload=typed_payload,
            raw_payload=payload,
            installation_id=installation_id,
            repo=extract_repository_ref(payload),
            sender=extract_sender_ref(payload),
            github=github_client,
            log=bound,
            request=request,
            _config_loader=self._config_loader,
        )

        for handler in handlers:
            start = time.perf_counter()
            handler_name = getattr(handler, "__name__", repr(handler))
            try:
                await handler(ctx)
                duration_ms = int((time.perf_counter() - start) * 1000)
                ctx.log.info(
                    "github_handler_completed",
                    extra={
                        "qualified_event": qualified_event,
                        "handler": handler_name,
                        "status": "success",
                        "duration_ms": duration_ms,
                    },
                )
            except Exception as exc:
                duration_ms = int((time.perf_counter() - start) * 1000)
                ctx.log.warning(
                    "github_handler_failed",
                    extra={
                        "qualified_event": qualified_event,
                        "handler": handler_name,
                        "status": "error",
                        "duration_ms": duration_ms,
                        "error_type": type(exc).__name__,
                    },
                )
                error = HandlerError(
                    exc=exc,
                    context=ctx,
                    handler=handler,
                    qualified_event=qualified_event,
                )
                await self._dispatch_error_hooks(error)

    async def _dispatch_error_hooks(self, error: HandlerError) -> None:
        for hook in self._registry.error_handlers():
            try:
                await hook(error)
            except Exception as hook_exc:  # pragma: no cover - defensive
                logging.getLogger("ghappkit").exception(
                    "github_error_hook_failed",
                    exc_info=hook_exc,
                )

    async def _create_github_client(self, installation_id: int | None) -> GitHubClient:
        if self._client_factory is not None:
            return cast("GitHubClient", await self._client_factory(installation_id))
        if installation_id is None:
            return MissingInstallationGitHubClient()
        if self._token_provider is None:
            raise GitHubApiError(
                "GitHub App private key is not configured but installation ID was present",
                status_code=None,
            )
        token = await self._token_provider.get_token(installation_id)
        return DefaultGitHubClient(
            http_client=self._http_client,
            api_base_url=str(self.settings.github_api_url),
            token=token.token,
        )

    def _repo_slug(self, payload: Mapping[str, Any]) -> str | None:
        repo = payload.get("repository")
        if not isinstance(repo, dict):
            return None
        owner = repo.get("owner")
        name = repo.get("name")
        if (
            isinstance(owner, dict)
            and isinstance(owner.get("login"), str)
            and isinstance(name, str)
        ):
            return f"{owner['login']}/{name}"
        return None

    def _sender_login(self, payload: Mapping[str, Any]) -> str | None:
        sender = payload.get("sender")
        if isinstance(sender, dict) and isinstance(sender.get("login"), str):
            return sender["login"]
        return None

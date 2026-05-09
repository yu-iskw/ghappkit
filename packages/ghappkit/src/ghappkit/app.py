"""Primary FastAPI integration surface."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextvars import ContextVar
from typing import Any, Final, NoReturn, cast

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from ghappkit_client.auth import load_private_key_pem
from ghappkit_client.client import DefaultGitHubClient, GitHubClient
from ghappkit_client.errors import GhappkitError, GitHubApiError, InstallationAuthError
from ghappkit_client.token_provider import InstallationTokenProvider

from ghappkit.context import (
    BoundLogger,
    WebhookContext,
    build_payload_model,
    extract_installation_id,
    extract_repository_ref,
    extract_sender_ref,
)
from ghappkit.delivery_logging import delivery_logger, ensure_delivery_log_sanitize_filter
from ghappkit.event_resolution import resolve_qualified_webhook_event
from ghappkit.exceptions import (
    ErrorHookExecutionError,
    EventModelError,
    HandlerError,
    HandlerExecutionError,
    PayloadParseError,
    RepoConfigError,
    WebhookHeaderError,
    WebhookSignatureError,
)
from ghappkit.execution import (
    DeliveryExecutor,
    FastAPIBackgroundExecutor,
    InlineExecutor,
    NoopExecutor,
)
from ghappkit.headers import GitHubDeliveryHeaders
from ghappkit.payload import parse_json_payload
from ghappkit.repo_config import RepoConfigLoader
from ghappkit.routing import ErrorHook, EventRegistry, Handler
from ghappkit.settings import GitHubAppSettings
from ghappkit.stub_github import MissingInstallationGitHubClient
from ghappkit.webhooks import parse_delivery_after_optional_signature

_LOGGER = logging.getLogger("ghappkit")

_MISSING_INSTALL_CLIENT: Final = MissingInstallationGitHubClient()

_delivery_failure_phase: ContextVar[str] = ContextVar(
    "ghappkit_delivery_failure_phase",
    default="unknown",
)

# (exception type, HTTP 500 ``detail``). Order matters for ``isinstance`` if types ever
# inherit from one another; keep ``GitHubApiError`` before ``InstallationAuthError``.
# This sequence also defines which exceptions must propagate from ``enqueue`` when the
# executor **awaits** the task (``InlineExecutor``): ``FastAPIBackgroundExecutor.enqueue``
# only schedules work and does not await it, so failures in background tasks still do not
# reach ``GitHubApp.router`` after GitHub has received 202 (see ``webhook_ack_before_dispatch``).
_WEBHOOK_MAPPED_INTERNAL_ERRORS: tuple[tuple[type[Exception], str], ...] = (
    (HandlerExecutionError, "webhook_handler_failed"),
    (ErrorHookExecutionError, "webhook_error_hook_failed"),
    (EventModelError, "webhook_event_model_invalid"),
    (GitHubApiError, "webhook_github_api_error"),
    (InstallationAuthError, "webhook_installation_auth_error"),
    (RepoConfigError, "webhook_repo_config_error"),
)

_WEBHOOK_DELIVERY_EXCEPTIONS_TO_RERAISE: tuple[type[Exception], ...] = tuple(
    pair[0] for pair in _WEBHOOK_MAPPED_INTERNAL_ERRORS
)

_WEBHOOK_PAYLOAD_PARSE_HTTP_DETAIL: dict[str, str] = {
    "utf8": "invalid_webhook_payload_encoding",
    "json": "invalid_webhook_payload_json",
    "not_object": "invalid_webhook_payload_not_object",
}


def _chain_handler_failure(
    exc: BaseException,
    *,
    handler_name: str,
    qualified_event: str,
) -> HandlerExecutionError:
    """Wrap a user handler failure with a stable type and exception chain."""
    err = HandlerExecutionError(
        f"handler {handler_name} failed for {qualified_event}: {type(exc).__name__}",
    )
    err.__cause__ = exc
    return err


def _raise_http_for_webhook_route_failure(exc: Exception) -> NoReturn:
    """Translate framework delivery errors to HTTP responses (always raises).

    All :class:`WebhookSignatureError` subclasses share the same 401 ``detail`` so clients
    can treat any signature problem as unauthorized without parsing subtypes.

    Internal server errors for mapped types are driven by ``_WEBHOOK_MAPPED_INTERNAL_ERRORS``.
    Client-facing HTTP 400 responses use stable ``detail`` strings (no exception message
    passthrough). Payload parse failures map to ``invalid_webhook_payload_encoding``,
    ``invalid_webhook_payload_json``, or ``invalid_webhook_payload_not_object`` depending
    on failure mode; header problems use ``invalid_webhook_headers``.
    """
    if isinstance(exc, WebhookSignatureError):
        raise HTTPException(status_code=401, detail="invalid_webhook_signature") from exc
    if isinstance(exc, WebhookHeaderError):
        raise HTTPException(status_code=400, detail="invalid_webhook_headers") from exc
    if isinstance(exc, PayloadParseError):
        detail = _WEBHOOK_PAYLOAD_PARSE_HTTP_DETAIL.get(
            exc.kind,
            "invalid_webhook_payload",
        )
        raise HTTPException(status_code=400, detail=detail) from exc
    for exc_cls, detail in _WEBHOOK_MAPPED_INTERNAL_ERRORS:
        if isinstance(exc, exc_cls):
            raise HTTPException(status_code=500, detail=detail) from exc
    raise HTTPException(
        status_code=500,
        detail=f"webhook delivery failed ({type(exc).__name__})",
    ) from exc


class GitHubApp:
    """FastAPI-native GitHub App registry.

    **Webhook handler matching:** By default only the qualified event name (for example
    ``issues.opened``) and catch-all handlers run. To restore older behavior where
    handlers registered for the base GitHub event (``issues``) also run for actionable
    payloads, set :attr:`GitHubAppSettings.webhook_match_legacy_base_event_handlers` to
    ``True``.
    """

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
        built_token_provider = self._maybe_build_token_provider()
        self._token_provider = token_provider or built_token_provider
        self._config_loader = RepoConfigLoader(settings, ttl_seconds=config_ttl_seconds)
        self._client_factory = github_client_factory
        ensure_delivery_log_sanitize_filter(_LOGGER)
        if (
            token_provider is None
            and built_token_provider is not None
            and self.settings.app_id == 0
        ):
            raise ValueError(
                "GitHubAppSettings.app_id must be a non-zero GitHub App ID when a "
                "private key is configured (installation token / JWT flow). Webhook-only "
                "setups should omit GITHUB_APP_PRIVATE_KEY and GITHUB_APP_PRIVATE_KEY_PATH.",
            )

    def _handlers_for_delivery(
        self,
        qualified_event: str,
        headers: GitHubDeliveryHeaders,
    ) -> list[Handler]:
        base = (
            headers.event
            if self.settings.webhook_match_legacy_base_event_handlers
            else None
        )
        return self._registry.handlers_for(qualified_event, base_event=base)

    async def aclose(self) -> None:
        """Close resources owned by this app (for example the default ``httpx.AsyncClient``)."""
        if self._owns_http_client:
            await self._http_client.aclose()

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

        def decorator(handler: ErrorHook) -> ErrorHook:
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
                    header_map=request.headers,
                )
            except HTTPException:
                raise
            except GhappkitError as exc:
                _raise_http_for_webhook_route_failure(exc)

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
        secret = self.settings.webhook_secret.get_secret_value()
        headers = parse_delivery_after_optional_signature(
            raw_body=body,
            header_map=header_map,
            webhook_secret=secret,
            require_signature=verify_signature,
        )
        inline_parse = not (
            self.settings.webhook_ack_before_dispatch
            and isinstance(executor, FastAPIBackgroundExecutor)
        )
        return await self._dispatch_handlers(
            request,
            headers,
            body,
            executor,
            inline_payload_validation=inline_parse,
        )

    async def _dispatch_handlers(
        self,
        request: Request | None,
        headers: GitHubDeliveryHeaders,
        body: bytes,
        executor: DeliveryExecutor,
        *,
        inline_payload_validation: bool = True,
    ) -> Response:
        if inline_payload_validation:
            return await self._dispatch_after_parse(
                request,
                headers,
                body,
                executor,
            )

        async def deferred_delivery() -> None:
            try:
                payload = parse_json_payload(body)
            except PayloadParseError:
                _LOGGER.warning(
                    "github_webhook_payload_invalid",
                    extra={
                        "delivery_id": headers.delivery_id,
                        "event": headers.event,
                        "failure": "invalid_json",
                        "webhook_phase": "parse",
                    },
                )
                return
            qualified, payload_action = resolve_qualified_webhook_event(headers.event, payload)
            handlers = self._handlers_for_delivery(qualified, headers)
            if isinstance(executor, NoopExecutor):
                return
            if not handlers:
                return
            await self._invoke_handlers_guarded(
                executor,
                request,
                headers,
                payload,
                qualified,
                handlers,
                payload_action=payload_action,
            )

        try:
            await executor.enqueue(deferred_delivery)
        except Exception as exc:
            if isinstance(exc, _WEBHOOK_DELIVERY_EXCEPTIONS_TO_RERAISE):
                raise
            raise HTTPException(
                status_code=500,
                detail=f"failed to schedule webhook handlers ({type(exc).__name__})",
            ) from exc

        return Response(status_code=202)

    async def _dispatch_after_parse(
        self,
        request: Request | None,
        headers: GitHubDeliveryHeaders,
        body: bytes,
        executor: DeliveryExecutor,
    ) -> Response:
        payload = parse_json_payload(body)
        qualified, payload_action = resolve_qualified_webhook_event(headers.event, payload)
        handlers = self._handlers_for_delivery(qualified, headers)

        if isinstance(executor, NoopExecutor):
            return Response(status_code=202)
        if not handlers:
            return Response(status_code=202)

        async def task() -> None:
            await self._invoke_handlers_guarded(
                executor,
                request,
                headers,
                payload,
                qualified,
                handlers,
                payload_action=payload_action,
            )

        try:
            await executor.enqueue(task)
        except Exception as exc:
            if isinstance(exc, _WEBHOOK_DELIVERY_EXCEPTIONS_TO_RERAISE):
                raise
            raise HTTPException(
                status_code=500,
                detail=f"failed to schedule webhook handlers ({type(exc).__name__})",
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
        secret = self.settings.webhook_secret.get_secret_value()
        hdrs = parse_delivery_after_optional_signature(
            raw_body=body,
            header_map=headers,
            webhook_secret=secret,
            require_signature=False,
        )
        return await self._dispatch_handlers(
            request,
            hdrs,
            body,
            chosen,
            inline_payload_validation=True,
        )

    async def _invoke_handlers_guarded(
        self,
        executor: DeliveryExecutor,
        request: Request | None,
        headers: GitHubDeliveryHeaders,
        payload: dict[str, Any],
        qualified_event: str,
        handlers: Sequence[Handler],
        *,
        payload_action: str | None,
    ) -> None:
        """Run handlers; log full failures when work is deferred (GitHub already got 202)."""
        try:
            await self._invoke_handlers(
                request,
                headers,
                payload,
                qualified_event,
                handlers,
                payload_action=payload_action,
            )
        except Exception as exc:
            if isinstance(executor, FastAPIBackgroundExecutor):
                extra: dict[str, Any] = {
                    "delivery_id": headers.delivery_id,
                    "event": headers.event,
                    "qualified_event": qualified_event,
                    "failure_phase": _delivery_failure_phase.get(),
                    "error_type": type(exc).__name__,
                }
                if isinstance(exc, ErrorHookExecutionError):
                    extra["failure_source"] = "error_hook"
                else:
                    extra["failure_source"] = "handler_or_framework"
                _LOGGER.exception(
                    "github_webhook_handler_delivery_failed",
                    extra=extra,
                )
                return
            raise

    async def _invoke_handlers(
        self,
        request: Request | None,
        headers: GitHubDeliveryHeaders,
        payload: dict[str, Any],
        qualified_event: str,
        handlers: Sequence[Handler],
        *,
        payload_action: str | None,
    ) -> None:
        _delivery_failure_phase.set("github_client")
        installation_id = extract_installation_id(payload)
        github_client = await self._create_github_client(installation_id)
        repo_ref = extract_repository_ref(payload)
        sender_ref = extract_sender_ref(payload)
        structured = delivery_logger(
            _LOGGER,
            delivery_id=headers.delivery_id,
            qualified_event=qualified_event,
            installation_id=installation_id,
            repository=f"{repo_ref.owner}/{repo_ref.name}" if repo_ref else None,
            sender=sender_ref.login if sender_ref else None,
        )
        bound = BoundLogger(structured.logger, structured.extra)
        _delivery_failure_phase.set("payload_model")
        typed_payload = build_payload_model(qualified_event, payload)
        _delivery_failure_phase.set("context_build")
        ctx = WebhookContext(
            delivery_id=headers.delivery_id,
            event=headers.event,
            qualified_event=qualified_event,
            action=payload_action,
            payload=typed_payload,
            raw_payload=payload,
            installation_id=installation_id,
            repo=repo_ref,
            sender=sender_ref,
            github=github_client,
            log=bound,
            request=request,
            _config_loader=self._config_loader,
        )

        _delivery_failure_phase.set("handlers")
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
            except Exception as exc:  # pylint: disable=broad-exception-caught
                duration_ms = int((time.perf_counter() - start) * 1000)
                wrapped = _chain_handler_failure(
                    exc,
                    handler_name=handler_name,
                    qualified_event=qualified_event,
                )
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
                    exc=wrapped,
                    context=ctx,
                    handler=handler,
                    qualified_event=qualified_event,
                )
                await self._dispatch_error_hooks(error)
                raise wrapped from exc

    async def _dispatch_error_hooks(self, error: HandlerError) -> None:
        """Run registered ``on_error`` hooks in registration order.

        Each hook is awaited sequentially; if a hook raises, later hooks do not run and
        there is no rollback of side effects from hooks that already completed.
        """
        for hook in self._registry.error_handlers():
            await self._invoke_error_hook(hook, error)

    async def _invoke_error_hook(self, hook: ErrorHook, error: HandlerError) -> None:
        try:
            await hook(error)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _LOGGER.exception("github_error_hook_failed")
            raise ErrorHookExecutionError(
                "registered GitHub webhook error hook failed",
            ) from exc

    async def _create_github_client(self, installation_id: int | None) -> GitHubClient:
        if self._client_factory is not None:
            return cast("GitHubClient", await self._client_factory(installation_id))
        if installation_id is None:
            return _MISSING_INSTALL_CLIENT
        if self._token_provider is None:
            return _MISSING_INSTALL_CLIENT
        token = await self._token_provider.get_token(installation_id)
        return DefaultGitHubClient(
            http_client=self._http_client,
            api_base_url=str(self.settings.github_api_url),
            token=token.token,
        )

"""Azure OpenAI backed Playwright test generation for Proven miners."""

from __future__ import annotations

import ast
import os
import re
import textwrap
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse


DEFAULT_API_VERSION = "2025-01-01-preview"
DEFAULT_DEPLOYMENT = "gpt-4.1"
DEFAULT_MAX_COMPLETION_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.2


class AIConfigurationError(RuntimeError):
    """Raised when AI generation is requested but not configured correctly."""


@dataclass(frozen=True)
class AzureOpenAIConfig:
    """Runtime settings for Azure OpenAI chat completions."""

    endpoint: str
    api_key: str
    deployment: str = DEFAULT_DEPLOYMENT
    api_version: str = DEFAULT_API_VERSION
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    top_p: float = 1.0

    @classmethod
    def from_env(cls) -> Optional["AzureOpenAIConfig"]:
        """Build config from env vars, returning None when credentials are absent."""

        target_endpoint = ""
        target_deployment = ""
        target_api_version = ""

        target_uri = os.environ.get("AZURE_OPENAI_TARGET_URI", "").strip()
        if target_uri:
            target_endpoint, target_deployment, target_api_version = _parse_target_uri(
                target_uri
            )

        endpoint = (
            os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
            or target_endpoint
        )
        api_key = (
            os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
            or os.environ.get("AZURE_OPENAI_KEY", "").strip()
        )
        deployment = (
            os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip()
            or os.environ.get("AZURE_OPENAI_MODEL", "").strip()
            or target_deployment
            or DEFAULT_DEPLOYMENT
        )
        api_version = (
            os.environ.get("AZURE_OPENAI_API_VERSION", "").strip()
            or target_api_version
            or DEFAULT_API_VERSION
        )

        if not endpoint or not api_key:
            return None

        return cls(
            endpoint=endpoint.rstrip("/") + "/",
            api_key=api_key,
            deployment=deployment,
            api_version=api_version,
            max_completion_tokens=_env_int(
                "AZURE_OPENAI_MAX_COMPLETION_TOKENS",
                DEFAULT_MAX_COMPLETION_TOKENS,
            ),
            temperature=_env_float(
                "AZURE_OPENAI_TEMPERATURE",
                DEFAULT_TEMPERATURE,
            ),
            top_p=_env_float("AZURE_OPENAI_TOP_P", 1.0),
        )


class AzurePlaywrightGenerator:
    """Generates pytest-playwright scripts from Proven verification specs."""

    def __init__(self, config: AzureOpenAIConfig):
        self.config = config
        self._client = None

    @classmethod
    def from_env(cls) -> Optional["AzurePlaywrightGenerator"]:
        config = AzureOpenAIConfig.from_env()
        if config is None:
            return None
        return cls(config)

    def generate_script(
        self,
        *,
        spec_type: str,
        requirement_content: str,
        target_url: str,
    ) -> str:
        response = self._get_client().chat.completions.create(
            model=self.config.deployment,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {
                    "role": "user",
                    "content": _user_prompt(
                        spec_type=spec_type,
                        requirement_content=requirement_content,
                        target_url=target_url,
                    ),
                },
            ],
            max_completion_tokens=self.config.max_completion_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )

        content = response.choices[0].message.content or ""
        script = extract_python_code(content)
        validate_playwright_script(script)
        return script

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            from openai import AzureOpenAI
        except ImportError as exc:
            raise AIConfigurationError(
                "OpenAI SDK is not installed. Install requirements or run `pip install openai`."
            ) from exc

        self._client = AzureOpenAI(
            api_version=self.config.api_version,
            azure_endpoint=self.config.endpoint,
            api_key=self.config.api_key,
        )
        return self._client


def build_fallback_script(target_url: str = "http://localhost:8080") -> str:
    """Current deterministic Willify prototype script used when AI is unavailable."""

    return textwrap.dedent(
        f"""
        import os
        from playwright.sync_api import Page, expect

        TARGET_URL = os.environ.get("TARGET_URL", {target_url!r})

        def test_willify_core_features(page: Page):
            page.goto(f"{{TARGET_URL}}/src/html/index.html")

            read_more_btn = page.locator("#read-more-button")
            expect(read_more_btn).to_be_visible()

            heading = page.locator("h3")
            expect(heading).to_have_text("Where Music Meets Comfort")

            register_btn = page.locator("#sign-up")
            expect(register_btn).to_have_attribute("href", "register.html")
        """
    ).strip()


def extract_python_code(content: str) -> str:
    """Accept either raw Python or a fenced markdown block and return Python code."""

    fenced = re.search(
        r"```(?:python|py)?\s*(?P<code>.*?)```",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    script = fenced.group("code") if fenced else content
    return script.strip()


def validate_playwright_script(script: str) -> None:
    """Apply a small static gate before returning miner-generated code."""

    if not script:
        raise ValueError("AI response did not contain a Python script.")

    try:
        tree = ast.parse(script)
    except SyntaxError as exc:
        raise ValueError(f"AI generated invalid Python: {exc}") from exc

    banned_import_roots = {
        "asyncio",
        "httpx",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "sys",
        "urllib",
    }
    allowed_import_roots = {"os", "playwright", "pytest", "re", "typing"}
    banned_calls = {
        "__import__",
        "compile",
        "eval",
        "exec",
        "globals",
        "input",
        "locals",
        "open",
        "vars",
    }
    banned_call_prefixes = (
        "os.remove",
        "os.rename",
        "os.replace",
        "os.rmdir",
        "os.system",
        "os.unlink",
        "os.walk",
        "shutil.",
        "socket.",
        "subprocess.",
        "time.sleep",
    )

    has_playwright_import = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in banned_import_roots or root not in allowed_import_roots:
                    raise ValueError(f"Disallowed import in generated script: {alias.name}")
                has_playwright_import = has_playwright_import or root == "playwright"

        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in banned_import_roots or root not in allowed_import_roots:
                raise ValueError(f"Disallowed import in generated script: {node.module}")
            has_playwright_import = has_playwright_import or root == "playwright"

        if isinstance(node, ast.Call):
            name = _dotted_name(node.func)
            if name in banned_calls or name.endswith(".__call__"):
                raise ValueError(f"Disallowed call in generated script: {name}")
            if any(name == prefix[:-1] or name.startswith(prefix) for prefix in banned_call_prefixes):
                raise ValueError(f"Disallowed call in generated script: {name}")

    if not has_playwright_import:
        raise ValueError("Generated script must import Playwright.")


def _parse_target_uri(target_uri: str) -> Tuple[str, str, str]:
    parsed = urlparse(target_uri)
    endpoint = f"{parsed.scheme}://{parsed.netloc}/" if parsed.scheme and parsed.netloc else ""

    deployment = ""
    marker = "/openai/deployments/"
    if marker in parsed.path:
        deployment = unquote(parsed.path.split(marker, 1)[1].split("/", 1)[0])

    api_version = parse_qs(parsed.query).get("api-version", [""])[0]
    return endpoint, deployment, api_version


def _system_prompt() -> str:
    return textwrap.dedent(
        """
        You generate deterministic pytest-playwright Python files for Proven, a
        Bittensor software verification subnet.

        Return only a single Python file. Do not include markdown, prose, JSON,
        or explanations. The file will be executed twice by a validator: first
        against a clean reference application, then against one or more mutated
        applications. Good tests pass on the clean app and fail only when the
        target violates the requested specification.

        Hard requirements:
        - Use pytest-playwright with `from playwright.sync_api import Page, expect`.
        - Read the app host from `TARGET_URL = os.environ.get("TARGET_URL", ...)`.
        - Prefer Playwright locators and expect assertions over sleeps.
        - Keep tests self-contained and deterministic.
        - Do not use subprocesses, filesystem access, external HTTP clients,
          raw sockets, eval, exec, or destructive OS operations.
        - Do not crawl the whole DOM or inspect implementation details unrelated
          to the specification.
        """
    ).strip()


def _user_prompt(
    *,
    spec_type: str,
    requirement_content: str,
    target_url: str,
) -> str:
    return textwrap.dedent(
        f"""
        Generate a pytest-playwright Python test file for this Proven task.

        Spec type:
        {spec_type or "user_story"}

        Requirement:
        {requirement_content}

        Target base URL:
        {target_url}

        Include this exact target bootstrap near the top:
        TARGET_URL = os.environ.get("TARGET_URL", {target_url!r})

        The validator will set TARGET_URL to the reference or mutant app before
        running the same file. Return Python code only.
        """
    ).strip()


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default

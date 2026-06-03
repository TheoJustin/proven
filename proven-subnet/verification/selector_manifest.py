"""Feature-area scoped selector manifest builder for Willify references."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from html.parser import HTMLParser


@dataclass(frozen=True)
class SelectorEntry:
    key: str
    selector: str
    role: str | None = None
    accessible_name: str | None = None
    state: dict[str, str] | None = None


class _ManifestParser(HTMLParser):
    def __init__(self, feature_area: str):
        super().__init__(convert_charrefs=True)
        self.feature_area = feature_area
        self.stack: list[dict] = []
        self.entries: list[SelectorEntry] = []

    def handle_starttag(self, tag: str, attrs):
        attr = dict(attrs)
        in_scope = self._in_scope(attr)
        frame = {"tag": tag, "attrs": attr, "text": [], "scope": in_scope}
        self.stack.append(frame)
        if (
            in_scope
            and self._is_interactive(tag, attr)
            and (tag in {"input", "select", "textarea"} or attr.get("aria-label"))
        ):
            self.entries.append(self._entry(tag, attr))

    def handle_data(self, data: str):
        if self.stack:
            self.stack[-1]["text"].append(data)

    def handle_endtag(self, tag: str):
        if not self.stack:
            return
        frame = self.stack.pop()
        text = " ".join("".join(frame["text"]).split())
        if (
            frame["scope"]
            and text
            and (
                self._is_heading(frame["tag"], frame["attrs"])
                or self._is_interactive(frame["tag"], frame["attrs"])
            )
        ):
            self.entries.append(self._entry(frame["tag"], frame["attrs"], text))
        if self.stack and text:
            self.stack[-1]["text"].append(text)

    def _in_scope(self, attrs: dict[str, str]) -> bool:
        if any(frame["scope"] for frame in self.stack):
            return True
        needle = self.feature_area.replace("_", "-").lower()
        values = " ".join(str(v) for v in attrs.values()).lower()
        return needle in values or self.feature_area.lower() in values

    def _is_interactive(self, tag: str, attrs: dict[str, str]) -> bool:
        return tag in {"a", "button", "input", "select", "textarea"} or "role" in attrs

    def _is_heading(self, tag: str, attrs: dict[str, str]) -> bool:
        return (
            tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
            or attrs.get("role") == "heading"
        )

    def _entry(
        self, tag: str, attrs: dict[str, str], text: str | None = None
    ) -> SelectorEntry:
        selector = _best_selector(tag, attrs)
        key = _key(attrs, text or attrs.get("aria-label") or selector)
        return SelectorEntry(
            key=key,
            selector=selector,
            role=attrs.get("role") or _implicit_role(tag, attrs),
            accessible_name=attrs.get("aria-label") or text,
            state={
                k: v
                for k, v in attrs.items()
                if k.startswith("aria-") or k in {"disabled", "checked"}
            }
            or None,
        )


def build_selector_manifest(
    html: str,
    feature_area: str,
    *,
    enabled: bool = True,
) -> dict:
    """Build a serialisable selector manifest from reference HTML.

    The ``enabled`` flag is the bootstrapping/private-audit switch requested by
    ADR-0003: when disabled, no DOM selectors are emitted.
    """

    if not enabled:
        return {"feature_area": feature_area, "selectors": {}, "entries": []}
    parser = _ManifestParser(feature_area)
    parser.feed(html)
    entries = parser.entries
    return {
        "feature_area": feature_area,
        "selectors": {entry.key: entry.selector for entry in entries},
        "entries": [asdict(entry) for entry in entries],
    }


def _best_selector(tag: str, attrs: dict[str, str]) -> str:
    if attrs.get("data-testid"):
        return f"[data-testid='{attrs['data-testid']}']"
    if attrs.get("id"):
        return f"#{attrs['id']}"
    if attrs.get("aria-label"):
        return f"{tag}[aria-label='{attrs['aria-label']}']"
    if attrs.get("href") and tag == "a":
        return f"a[href='{attrs['href']}']"
    classes = attrs.get("class", "").split()
    if classes:
        return tag + "".join(f".{cls}" for cls in classes[:2])
    return tag


def _key(attrs: dict[str, str], label: str) -> str:
    raw = attrs.get("data-testid") or attrs.get("id") or label or "element"
    chars = [c.lower() if c.isalnum() else "_" for c in raw]
    key = "".join(chars).strip("_")
    return key or "element"


def _implicit_role(tag: str, attrs: dict[str, str]) -> str | None:
    if tag == "a" and attrs.get("href"):
        return "link"
    if tag == "button":
        return "button"
    if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
        return "heading"
    if tag == "input":
        return "textbox"
    return None

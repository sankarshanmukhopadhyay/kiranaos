#!/usr/bin/env python3
"""Validate GitHub Pages documentation structure and publication coverage."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ROOT_MIRRORS = {
    "README.md": DOCS / "project" / "readme.md",
    "ROADMAP.md": DOCS / "project" / "roadmap.md",
    "CHANGELOG.md": DOCS / "project" / "changelog.md",
    "CONTRIBUTING.md": DOCS / "project" / "contributing.md",
    "SECURITY.md": DOCS / "project" / "security.md",
    "LICENSE": DOCS / "project" / "license.md",
}

errors: list[str] = []
pages: dict[str, Path] = {}
parents: set[str] = set()


def front_matter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append(f"{path.relative_to(ROOT)}: missing YAML front matter")
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        errors.append(f"{path.relative_to(ROOT)}: unterminated YAML front matter")
        return {}, text
    raw = text[4:end]
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"\'')
    return data, text[end + 5 :]


for path in sorted(DOCS.rglob("*.md")):
    meta, body = front_matter(path)
    title = meta.get("title")
    if not title:
        errors.append(f"{path.relative_to(ROOT)}: missing title")
    else:
        pages[title] = path
    if meta.get("has_children") == "true" and title:
        parents.add(title)
    if path.name != "index.md" and not meta.get("permalink"):
        errors.append(f"{path.relative_to(ROOT)}: missing stable permalink")
    if body.count("```mermaid") > body.count("```"):
        errors.append(f"{path.relative_to(ROOT)}: unclosed Mermaid fence")

for title, path in pages.items():
    meta, _ = front_matter(path)
    parent = meta.get("parent")
    if parent and parent not in parents:
        errors.append(f"{path.relative_to(ROOT)}: unknown navigation parent {parent!r}")

# Markdown links under docs must resolve unless they are external, anchors, Liquid links, or API examples.
link_re = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
for path in sorted(DOCS.rglob("*.md")):
    _, body = front_matter(path)
    for raw in link_re.findall(body):
        target = raw.split()[0].strip("<>")
        if target.startswith(("http://", "https://", "mailto:", "tel:", "#", "{%")):
            continue
        clean = target.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        resolved = (path.parent / clean).resolve()
        if not resolved.exists():
            errors.append(f"{path.relative_to(ROOT)}: broken link {target!r}")

# Ensure every repository governance document has a visible site mirror.
for source, mirror in ROOT_MIRRORS.items():
    if not mirror.exists():
        errors.append(f"Missing published mirror for {source}: {mirror.relative_to(ROOT)}")
        continue
    meta, body = front_matter(mirror)
    if meta.get("source_file") != f"/{source}":
        errors.append(f"{mirror.relative_to(ROOT)}: source_file must identify /{source}")
    source_heading = next((line for line in (ROOT / source).read_text(encoding="utf-8").splitlines() if line.startswith("#")), None)
    if source_heading and source_heading not in body:
        errors.append(f"{mirror.relative_to(ROOT)}: does not appear synchronized with {source}")

required = [
    ROOT / ".github" / "workflows" / "pages.yml",
    DOCS / "_config.yml",
    DOCS / "Gemfile",
    DOCS / "_includes" / "head_custom.html",
    DOCS / "_includes" / "footer_custom.html",
]
for path in required:
    if not path.exists():
        errors.append(f"Missing required publishing artifact: {path.relative_to(ROOT)}")

if errors:
    print("Documentation validation failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print(f"Documentation validation passed: {len(pages)} Markdown pages are publishable.")

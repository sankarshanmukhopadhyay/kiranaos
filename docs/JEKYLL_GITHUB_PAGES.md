---
layout: page
title: GitHub Pages and Jekyll
permalink: /jekyll-github-pages/
---

# GitHub Pages and Jekyll

The KiranaOS documentation is renderable with GitHub Pages using Jekyll.

## Recommended repository setting

In GitHub:

1. Open **Settings**.
2. Open **Pages**.
3. Set source to the default branch.
4. Set folder to `/docs`.
5. Save.

## Local preview

Use a standard GitHub Pages/Jekyll environment:

```bash
cd docs
bundle init
bundle add github-pages
bundle exec jekyll serve
```

The documentation site entry point is `docs/index.md`.

## Documentation rules

- Keep every documentation page in Markdown.
- Include Jekyll front matter on documentation pages.
- Avoid absolute local paths.
- Link to repository files using relative links.
- Keep release notes versioned under `docs/`.

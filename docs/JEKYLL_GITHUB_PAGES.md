---
layout: default
title: Documentation Publishing
parent: Guides
nav_order: 5
permalink: /guides/documentation-publishing/
---

# Documentation Publishing

The complete KiranaOS documentation set is published with GitHub Pages and the Just The Docs theme. The site includes product guides, technical references, operational procedures, release records, and mirrored repository-governance documents.

## Deployment model

The workflow at `.github/workflows/pages.yml` builds `docs/` with the pinned Ruby dependencies in `docs/Gemfile`, validates internal links, uploads the generated site as a Pages artifact, and deploys it. Configure **Settings → Pages → Source** as **GitHub Actions**.

## Local preview

```bash
cd docs
bundle install
bundle exec jekyll serve --baseurl ""
```

Open `http://127.0.0.1:4000`.

## Validation

```bash
python scripts/validate_docs.py
cd docs
bundle exec jekyll build --strict_front_matter
```

The validator checks front matter, internal Markdown links, navigation parents, mirrored root-document parity, and Mermaid fence balance.

## Authoring rules

- Every publishable Markdown page must be under `docs/` and have front matter.
- Use `{% raw %}{% link path/to/page.md %}{% endraw %}` for links between documentation pages.
- Assign each page a stable `permalink`, `parent`, and `nav_order`.
- Keep Mermaid diagrams in fenced `mermaid` blocks; the site renders them client-side with Mermaid 11.
- Update the corresponding mirror under `docs/project/` whenever a root governance document changes. `scripts/validate_docs.py` enforces parity.
- Run the local validation before opening a pull request.

# Documentation

This directory contains the documentation for bblocks-projects.

## Structure

```
docs/
├── mkdocs.yml          # MkDocs configuration
├── README.md           # This file
└── docs/               # Documentation content
    ├── index.md
    ├── getting-started.md
    ├── creating-projects.md
    ├── updating-projects.md
    └── adding-components.md
```

## Building Documentation

### Install Dependencies

```bash
# From project root
uv sync
```

This installs mkdocs-material and other dev dependencies.

### Serve Locally

```bash
cd docs
uv run mkdocs serve
```

Open http://127.0.0.1:8000 in your browser.

The site will auto-reload when you edit files.

### Build Static Site

```bash
cd docs
uv run mkdocs build
```

This generates the static site in `docs/site/`.

## Writing Documentation

Follow these principles:

- **Problem-first**: Start with user pain points before solutions
- **Example-rich**: Every concept needs working code with real output
- **Progressive**: Simple examples before complex ones
- **Active voice**: "You can..." not "It can be..."
- **Show errors**: Include failure cases and how to handle them

See the [doc-writing skill](../.claude/skills/doc-writing/) for complete guidelines.

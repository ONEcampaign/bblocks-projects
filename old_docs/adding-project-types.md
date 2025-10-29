# Adding New Project Types

This guide explains how to extend the template with new project types.

## Template Architecture

The template uses **organized conditionals** with a base + overlay pattern:

```
template/
├── common files (pyproject.toml, .pre-commit-config.yaml, etc.)
├── {% if project_type == 'package' %}...{% endif %}/
└── {% if project_type == 'research' %}...{% endif %}/
```

## Steps to Add a New Project Type

### 1. Update copier.yml

Add your new type to the `project_type` choices:

```yaml
project_type:
  type: str
  help: What type of project?
  choices:
    Package: package
    Research/Analysis: research
    Web API: webapi          # NEW
  default: package
```

### 2. Create Type-Specific Directory

Create a new conditional directory in template/:

```
template/
└── {% if project_type == 'webapi' %}webapi{% endif %}/
    ├── app/
    │   ├── __init__.py.jinja
    │   ├── main.py.jinja
    │   └── routes.py.jinja
    └── tests/
        └── test_api.py.jinja
```

### 3. Update Common Files

Add conditional sections to common files where needed:

**pyproject.toml.jinja:**
```toml
{% if project_type == 'webapi' %}
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
]
{% endif %}
```

**ci.yml.jinja:**
```yaml
{% if project_type == 'webapi' %}
  integration-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # API-specific tests
{% endif %}
```

### 4. Test Your Changes

```bash
# Generate a test project
copier copy . /tmp/test-webapi
cd /tmp/test-webapi

# Verify structure
uv sync
uv run ruff check .
{% if has_tests %}uv run pytest{% endif %}
```

### 5. Document

Update the main README.md with your new project type.

## Best Practices

1. **Minimize duplication**: Use common files for shared configuration
2. **Keep conditionals clear**: Use `{% if project_type == 'X' %}` consistently
3. **Test thoroughly**: Generate and validate each type
4. **Update docs**: Keep README.md and this guide current
5. **Follow conventions**: Match existing structure patterns

## Jinja2 Tips

### Conditional Directories

```
{% if project_type == 'mytype' %}mytype{% endif %}/
    file.py.jinja
```

### Conditional Files

```
{% if project_type == 'mytype' %}special_file.py{% endif %}.jinja
```

### Conditional Content in Files

```jinja
{% if project_type == 'mytype' %}
# Type-specific content
{% endif %}
```

## Examples

See existing `package` and `research` conditionals in:
- `template/pyproject.toml.jinja`
- `template/.pre-commit-config.yaml.jinja`
- `template/.github/workflows/ci.yml.jinja`

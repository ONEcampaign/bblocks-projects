# bblocks-projects

> A CLI for creating, updating, and auditing Python projects against a shared [Copier](https://copier.readthedocs.io/) template.

`bblocks-projects` is the ONE Campaign's tool for keeping its Python projects consistent. It scaffolds new repos, pulls template improvements into existing ones, adds individual pieces (pre-commit, CI, ruff config) to projects that didn't start from the template, and runs a health check against the standards.

## The four commands

```bash
uvx bblocks-projects create my-project   # scaffold a new project
uvx bblocks-projects update              # pull template changes into one you already have
uvx bblocks-projects add pre-commit      # install one piece into any Python project
uvx bblocks-projects doctor              # health-check a managed project
```

Everything else is flags on those four.

## Where to start

- **New here?** Walk through [Getting Started](getting-started.md) — about ten minutes, ending with a generated project and one working analysis function inside it.
- **Just need to do a thing?**
    - [Create a project](creating-projects.md)
    - [Update a project](updating-projects.md)
    - [Add components to an existing project](adding-components.md)
    - [Adopt a project that wasn't created from the template](adopting-an-existing-project.md)
    - [Run the doctor](running-the-doctor.md)
- **Picking between `package` and `project`?** Read [Package vs project](package-vs-project.md).
- **Looking up a flag or template variable?** [Reference](reference.md).

## Install

Requires Python 3.11+, `git`, and [`uv`](https://docs.astral.sh/uv/) on `PATH`. The recommended invocation is `uvx bblocks-projects ...`, which downloads the tool on demand and exits — no install step. For other install methods (`uv tool install`, `pipx`, `pip`), see the [package README](https://github.com/ONEcampaign/bblocks-projects/blob/main/bblocks-projects/README.md).

---

[Source](https://github.com/ONEcampaign/bblocks-projects) · [Issues](https://github.com/ONEcampaign/bblocks-projects/issues) · MIT — see [LICENSE](https://github.com/ONEcampaign/bblocks-projects/blob/main/LICENSE).

# Distributing AESDK

This document describes the public package release path for AESDK.

## Package Name

The configured package name is `aesdk`.

Before the first public release, confirm availability:

```bash
python -m pip index versions aesdk
```

or visit:

```text
https://pypi.org/project/aesdk/
```

If the name is taken, change `[project].name` in `pyproject.toml` before publishing. The Python import name can remain `aesdk` if the distribution name changes.

## License

The repository currently does not declare a license. Choose and commit a license before publishing publicly.

Common options:

- MIT: permissive and simple.
- Apache-2.0: permissive with explicit patent language.
- BSD-3-Clause: permissive academic-friendly option.

Do not publish copyrighted textbook PDFs or extracted long-form book text. AESDK should distribute only compact, paraphrased protocols, source metadata, and rule files.

## Local Build

Run from the repository root:

```powershell
python -m pip install --upgrade build twine
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
python -m build
python -m twine check dist/*
```

Fresh wheel smoke test:

```powershell
python -m venv .tmp/aesdk-wheel-smoke
.tmp/aesdk-wheel-smoke/Scripts/python -m pip install --upgrade pip
.tmp/aesdk-wheel-smoke/Scripts/python -m pip install (Get-ChildItem dist/*.whl | Select-Object -First 1).FullName
.tmp/aesdk-wheel-smoke/Scripts/python -c "import aesdk as ae; print(ae.agent_context('did').method_id)"
```

On macOS/Linux:

```bash
python -m pip install --upgrade build twine
rm -rf dist build
python -m build
python -m twine check dist/*
python -m venv .tmp/aesdk-wheel-smoke
.tmp/aesdk-wheel-smoke/bin/python -m pip install --upgrade pip
.tmp/aesdk-wheel-smoke/bin/python -m pip install dist/*.whl
.tmp/aesdk-wheel-smoke/bin/python -c "import aesdk as ae; print(ae.agent_context('did').method_id)"
```

## TestPyPI

Use TestPyPI before publishing to PyPI.

1. Create/claim the TestPyPI project.
2. Configure a Trusted Publisher for:
   - owner/repo: `ajolex/aesdk`
   - workflow: `publish.yml`
   - environment: `testpypi`
3. Run the `Publish` workflow manually.
4. Install from TestPyPI in a clean environment:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple aesdk
python -c "import aesdk as ae; print(ae.agent_context('did').method_id)"
```

## PyPI Trusted Publishing

For real releases, use PyPI Trusted Publishing rather than long-lived API tokens.

Configure a PyPI Trusted Publisher for:

- owner/repo: `ajolex/aesdk`
- workflow: `publish.yml`
- environment: `pypi`

The release workflow uses GitHub OIDC and `pypa/gh-action-pypi-publish`.

Official references:

- https://docs.pypi.org/trusted-publishers/
- https://packaging.python.org/guides/section-build-and-publish/

## Release Flow

1. Confirm `python -m pytest` passes.
2. Confirm `python -m build` and `python -m twine check dist/*` pass.
3. Confirm the version in `pyproject.toml`.
4. Update `CHANGELOG.md`.
5. Commit release prep.
6. Tag:

```bash
git tag v0.1.0
git push origin main --tags
```

7. Approve TestPyPI and PyPI environments in GitHub Actions.
8. Smoke test public install after publish.

## Agent Installation Smoke

After install, verify the primary public workflow:

```bash
python - <<'PY'
import aesdk as ae
ctx = ae.agent_context("did")
print(ctx.method_id)
print(ctx.protocol["name"])
PY
```

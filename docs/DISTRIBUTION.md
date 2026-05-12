# Publishing AESDK For Public Use

This page is for the person preparing AESDK for public release. The intended public audience is not mainly software developers; it is economics RAs, faculty, and applied researchers who want safer AI-assisted empirical work.

The release should therefore be judged by one question:

> Can a research team install AESDK, tell an AI agent to use it, and get useful econometric guardrails with minimal extra work?

## Before Publishing

Do these before uploading anything to PyPI:

1. Confirm the Apache-2.0 license remains appropriate for the project.
2. Confirm the package name `aesdk` is available on PyPI.
3. Confirm no textbook PDFs or long extracted textbook text are included in the package.
4. Run the tests.
5. Build the package.
6. Install the built wheel in a fresh environment and verify `import aesdk as ae`.

## Package Name

The current package name is `aesdk`.

Check availability:

```bash
python -m pip index versions aesdk
```

or open:

```text
https://pypi.org/project/aesdk/
```

If the name is already taken, choose a different distribution name before release. The import name can still remain:

```python
import aesdk as ae
```

## License

AESDK is licensed under Apache-2.0.

Apache-2.0 is a permissive open-source license. It is a good fit for a public research and AI tooling package because universities, labs, companies, and independent researchers can use and adapt the package, and the license includes explicit patent language.

Before release, confirm that all committed project files are intended to be covered by this license.

## Textbook Material

AESDK can cite and summarize textbook-backed method guidance, but it should not distribute copyrighted textbooks or long extracted passages.

Safe to distribute:

- compact method protocols
- rule files
- source metadata
- local source locators
- examples written for AESDK

Not safe to distribute:

- full textbook PDFs
- large extracted textbook markdown files
- long verbatim textbook passages

## Local Build Check

On Windows PowerShell:

```powershell
python -m pip install --upgrade build twine
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
python -m build
python -m twine check dist/*
```

On macOS/Linux:

```bash
python -m pip install --upgrade build twine
rm -rf dist build
python -m build
python -m twine check dist/*
```

## Fresh Install Check

After building, install the wheel into a clean environment.

Windows PowerShell:

```powershell
python -m venv .tmp/aesdk-wheel-smoke
.tmp/aesdk-wheel-smoke/Scripts/python -m pip install --upgrade pip
.tmp/aesdk-wheel-smoke/Scripts/python -m pip install (Get-ChildItem dist/*.whl | Select-Object -First 1).FullName
.tmp/aesdk-wheel-smoke/Scripts/python -c "import aesdk as ae; print(ae.agent_context('did').method_id)"
```

macOS/Linux:

```bash
python -m venv .tmp/aesdk-wheel-smoke
.tmp/aesdk-wheel-smoke/bin/python -m pip install --upgrade pip
.tmp/aesdk-wheel-smoke/bin/python -m pip install dist/*.whl
.tmp/aesdk-wheel-smoke/bin/python -c "import aesdk as ae; print(ae.agent_context('did').method_id)"
```

Expected output:

```text
did
```

## TestPyPI First

Use TestPyPI before the real PyPI release.

1. Create or claim the TestPyPI project.
2. Configure Trusted Publishing for:
   - repository: `ajolex/aesdk`
   - workflow: `publish.yml`
   - environment: `testpypi`
3. Run the GitHub `Publish` workflow manually.
4. Test install from TestPyPI:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple aesdk
python -c "import aesdk as ae; print(ae.agent_context('did').protocol['name'])"
```

## PyPI Release

Use PyPI Trusted Publishing. Do not use a long-lived API token unless there is a specific reason.

Configure PyPI Trusted Publishing for:

- repository: `ajolex/aesdk`
- workflow: `publish.yml`
- environment: `pypi`

Useful official references:

- https://docs.pypi.org/trusted-publishers/
- https://packaging.python.org/guides/section-build-and-publish/

## Release Flow

1. Update `CHANGELOG.md`.
2. Confirm tests pass.
3. Confirm the package builds.
4. Confirm fresh wheel install works.
5. Commit release prep.
6. Tag the release:

```bash
git tag v0.1.0
git push origin main --tags
```

7. Approve the TestPyPI and PyPI environments in GitHub Actions.
8. After publication, test a public install.

## Public Install Smoke Test

After the package is on PyPI:

```bash
pip install aesdk
python - <<'PY'
import aesdk as ae
ctx = ae.agent_context("did")
print(ctx.method_id)
print(ctx.protocol["name"])
PY
```

Expected output should mention `did` and `Differences-in-Differences`.

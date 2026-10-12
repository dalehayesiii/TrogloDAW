import pytest

from scripts.check_policy import changed_paths, is_doc, validate


@pytest.mark.parametrize(
    "title", ["feat: new beat", "fix(audio): repair export", "feat!: new catalog"]
)
def test_conventional_titles(title):
    assert validate(title, ["mmcore.py"]) is False


@pytest.mark.parametrize(
    "title", ["update stuff", "feat:no space", "Feat: uppercase", "docs!: break", "fix: "]
)
def test_reject_invalid_titles(title):
    with pytest.raises(ValueError):
        validate(title, ["README.md"])


def test_documentation_allowlist():
    assert validate("docs: explain release", ["README.md", "docs/development.md"])
    for path in [
        "mmcore.py",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
        ".agents/skills/a/SKILL.md",
        "docs/tool.py",
    ]:
        assert not is_doc(path)
        with pytest.raises(ValueError):
            validate("docs: hide code", ["README.md", path])


def test_renaming_code_to_docs_cannot_skip_build(monkeypatch):
    def diff(args):
        assert "--no-renames" in args
        return b"app.py\0README.md\0"

    monkeypatch.setattr("scripts.check_policy.subprocess.check_output", diff)
    with pytest.raises(ValueError):
        validate("docs: rename", changed_paths("HEAD^", "HEAD"))

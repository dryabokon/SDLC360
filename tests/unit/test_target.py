import pytest

from src.repo import GITHUB_RE, check_target


@pytest.mark.parametrize(
    "t", ["https://github.com/encode/httpx", "encode/httpx", "git@github.com:encode/httpx.git", "https://github.com/encode/httpx/"]
)
def test_github_forms(t):
    assert check_target(t) == {"kind": "github", "display": "encode/httpx"}
    assert GITHUB_RE.match(t)


def test_local_git_folder(make_repo):
    root = make_repo({"a.txt": "x"}, name="proj")
    assert check_target(str(root)) == {"kind": "local", "display": "proj"}


@pytest.mark.parametrize(
    ("t", "msg"), [("", "Enter a GitHub URL"), ("   ", "Enter a GitHub URL"), ("/no/such/dir", "Folder not found"), ("just words", "Not recognised")]
)
def test_rejects_bad_targets(t, msg):
    with pytest.raises(ValueError, match=msg):
        check_target(t)


def test_rejects_plain_folder(tmp_path):
    with pytest.raises(ValueError, match="not a git repository"):
        check_target(str(tmp_path))

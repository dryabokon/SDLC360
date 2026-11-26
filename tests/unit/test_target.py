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


def test_refresh_takes_the_default_branch_not_the_first_by_name(make_repo, tmp_path):
    """A detached cached clone used to land on the first branch by name (rich: a 2022 release branch)."""
    import subprocess

    from src.repo import refresh_clone

    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
    origin = make_repo({"a.txt": "old\n"}, name="origin")
    subprocess.run([*git, "branch", "0-old-release"], cwd=origin, check=True)  # sorts before "main"
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    subprocess.run(["git", "checkout", "-q", "--detach"], cwd=clone, check=True)  # as a refreshed cache clone is
    (origin / "a.txt").write_text("new\n", encoding="utf-8")
    subprocess.run([*git, "commit", "-qam", "newest on main"], cwd=origin, check=True)

    refresh_clone(clone)
    head = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=clone, capture_output=True, text=True, check=True).stdout.strip()
    assert head == "newest on main"
    refresh_clone(clone)  # and again, from detached
    assert (clone / "a.txt").read_text(encoding="utf-8") == "new\n"

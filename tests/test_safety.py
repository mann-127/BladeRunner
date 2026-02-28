from bladerunner.safety import CriticalOperation


def test_detects_critical_bash_command() -> None:
    checker = CriticalOperation()

    is_critical, reason = checker.is_critical_bash("rm -rf /tmp/data")

    assert is_critical is True
    assert reason == "Delete files with 'rm' command"


def test_allows_non_critical_bash_command() -> None:
    checker = CriticalOperation()

    is_critical, reason = checker.is_critical_bash("ls -la")

    assert is_critical is False
    assert reason is None


def test_detects_sensitive_file_write_paths_and_extensions() -> None:
    checker = CriticalOperation()

    is_critical_path, path_reason = checker.is_critical_file_write("/etc/hosts")
    is_critical_ext, ext_reason = checker.is_critical_file_write("secret.pem")

    assert is_critical_path is True
    assert "sensitive path" in path_reason
    assert is_critical_ext is True
    assert ".pem" in ext_reason


def test_detects_sensitive_reads_only_for_secret_locations() -> None:
    checker = CriticalOperation()

    env_read, env_reason = checker.is_critical_read("/workspace/.env")
    req_read, req_reason = checker.is_critical_read("requirements.txt")

    assert env_read is True
    assert "sensitive" in env_reason
    assert req_read is False
    assert req_reason is None

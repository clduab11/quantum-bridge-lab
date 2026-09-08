"""Private request evidence; all records are fabricated and offline."""

import hashlib
import multiprocessing
import os
import signal
import stat

import pytest

from qbridge.request_records import RequestRecords


@pytest.fixture
def locations(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    repo = tmp_path / "repo"
    repo.mkdir()
    return private, repo


def test_exact_bytes_digest_permissions_and_exclusive_write(locations):
    private, repo = locations
    data = b'{"fabricated":true}\n'
    with RequestRecords(private, public_repo=repo) as records:
        assert records.write("attempt-1.request.json", data) == hashlib.sha256(data).hexdigest()
        with pytest.raises(FileExistsError):
            records.write("attempt-1.request.json", b"replacement")
    file = private / "attempt-1.request.json"
    assert file.read_bytes() == data
    assert stat.S_IMODE(file.stat().st_mode) == 0o600


@pytest.mark.parametrize(
    "name", ["", ".", "..", "../outside", "/absolute", "nested/file", "a" * 181]
)
def test_nonflat_or_unsafe_names_never_create_a_file(locations, name):
    private, repo = locations
    with RequestRecords(private, public_repo=repo) as records:
        with pytest.raises(ValueError):
            records.write(name, b"fabricated")
    assert list(private.iterdir()) == []


def test_private_directory_must_be_outside_repository(locations):
    private, repo = locations
    with pytest.raises(ValueError):
        RequestRecords(private, public_repo=private.parent)


def test_symlink_directory_is_refused(locations, tmp_path):
    private, repo = locations
    link = tmp_path / "link"
    link.symlink_to(private, target_is_directory=True)
    with pytest.raises(OSError):
        RequestRecords(link, public_repo=repo)


def test_permissions_rechecked_before_write(locations):
    private, repo = locations
    with RequestRecords(private, public_repo=repo) as records:
        private.chmod(0o755)
        with pytest.raises(PermissionError):
            records.write("fabricated.json", b"{}")
    assert list(private.iterdir()) == []


def test_wrong_initial_directory_permissions_refused(locations):
    private, repo = locations
    private.chmod(0o755)
    with pytest.raises(PermissionError):
        RequestRecords(private, public_repo=repo)


def test_replaced_directory_does_not_redirect_a_record(locations):
    private, repo = locations
    moved = private.with_name("moved")
    with RequestRecords(private, public_repo=repo) as records:
        private.rename(moved)
        private.mkdir(mode=0o700)
        with pytest.raises(PermissionError, match="path changed"):
            records.write("fabricated.json", b"{}")
    assert list(private.iterdir()) == []
    assert list(moved.iterdir()) == []


def test_short_writes_are_completed_and_both_syncs_precede_success(locations, monkeypatch):
    private, repo = locations
    real_write, real_sync = os.write, os.fsync
    sync_modes = []

    def short_write(fd, data):
        return real_write(fd, data[:3])

    def record_sync(fd):
        sync_modes.append(os.fstat(fd).st_mode)
        real_sync(fd)

    monkeypatch.setattr(os, "write", short_write)
    monkeypatch.setattr(os, "fsync", record_sync)
    with RequestRecords(private, public_repo=repo) as records:
        records.write("short.bin", b"fabricated-bytes")
    assert (private / "short.bin").read_bytes() == b"fabricated-bytes"
    assert len(sync_modes) == 2
    assert stat.S_ISREG(sync_modes[0]) and stat.S_ISDIR(sync_modes[1])


@pytest.mark.parametrize("fail_on", [1, 2])
def test_sync_failure_never_returns_a_receipt_or_allows_overwrite(locations, monkeypatch, fail_on):
    private, repo = locations
    real_sync = os.fsync
    syncs = 0

    def fail_sync(fd):
        nonlocal syncs
        syncs += 1
        if syncs == fail_on:
            raise OSError("fabricated sync failure")
        real_sync(fd)

    monkeypatch.setattr(os, "fsync", fail_sync)
    with RequestRecords(private, public_repo=repo) as records:
        with pytest.raises(OSError, match="fabricated sync failure"):
            records.write("uncertain.bin", b"fabricated")
        with pytest.raises(FileExistsError):
            records.write("uncertain.bin", b"replay")
    assert (private / "uncertain.bin").read_bytes() == b"fabricated"


def test_zero_length_write_failure_preserves_partial_evidence(locations, monkeypatch):
    private, repo = locations
    monkeypatch.setattr(os, "write", lambda _fd, _data: 0)
    with RequestRecords(private, public_repo=repo) as records:
        with pytest.raises(OSError, match="short"):
            records.write("partial.bin", b"fabricated")
    assert (private / "partial.bin").exists()


def test_requires_bytes_and_open_store(locations):
    private, repo = locations
    records = RequestRecords(private, public_repo=repo)
    with pytest.raises(TypeError):
        records.write("fabricated.txt", "text")
    records.close()
    records.close()
    with pytest.raises(ValueError, match="closed"):
        records.write("fabricated.bin", b"data")
    assert list(private.iterdir()) == []


def test_successful_record_survives_writer_process_kill(locations):
    private, repo = locations
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe(duplex=False)

    def worker():
        parent.close()
        with RequestRecords(private, public_repo=repo) as records:
            child.send(records.write("before-dispatch.bin", b"fabricated outgoing request"))
            signal.pause()

    process = context.Process(target=worker)
    process.start()
    child.close()
    try:
        assert parent.poll(10), "child did not finish durable retention"
        digest = parent.recv()
        process.kill()
        process.join(5)
        assert not process.is_alive()
        data = (private / "before-dispatch.bin").read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        assert data == b"fabricated outgoing request"
    finally:
        if process.is_alive():
            process.kill()
            process.join(5)
        process.close()
        parent.close()

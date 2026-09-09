"""Exclusive, durable byte records for a future provider transport.

The caller must retain verified outgoing bytes BEFORE dispatch and received
bytes BEFORE parsing. A returned digest means both file and directory fsync
completed. An exception means do not dispatch; preserve any partial file for
reconciliation. This component sends nothing and makes no hardware durability
or independent evaluator-blinding claim. Sequential forked workers are allowed.
"""

import hashlib
import os
import re
import stat
from pathlib import Path


class RequestRecords:
    """Write once into an existing private directory outside the public repo.

    The directory descriptor pins the destination. Its ownership, permissions
    and path identity are checked before each write. Files are never replaced
    or automatically removed after a failure. The process owner can still
    inspect or alter private evidence; hashes are not an authenticity proof.
    """

    def __init__(self, directory, *, public_repo):
        self.directory = Path(directory).absolute()
        self._fd = None
        if self.directory.resolve().is_relative_to(Path(public_repo).resolve()):
            raise ValueError("request records must be outside the public repository")
        fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self._fd = fd
        try:
            self._check_open()
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        self._check_open()
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def _check_open(self):
        if self._fd is None:
            raise ValueError("request record store is closed")
        info = os.fstat(self._fd)
        current = self.directory.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise PermissionError("request record directory must be owner-only 0700")
        if not stat.S_ISDIR(current.st_mode) or (info.st_dev, info.st_ino) != (
            current.st_dev,
            current.st_ino,
        ):
            raise PermissionError("request record directory path changed")

    def write(self, name: str, data: bytes) -> str:
        """Retain bytes and return SHA-256 only after both durability checks.

        Safe flat filenames prevent a record from escaping the protected
        directory. Exclusive creation also refuses pre-existing symlinks.
        After any error, a caller must not reuse this name for another attempt.
        """
        self._check_open()
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,179}", name):
            raise ValueError("request record name must be a safe flat filename, at most 180 chars")
        if not isinstance(data, bytes):
            raise TypeError("request record payload must be bytes")
        fd = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=self._fd,
        )
        try:
            os.fchmod(fd, 0o600)
            view = memoryview(data)
            offset = 0
            while offset < len(view):
                written = os.write(fd, view[offset:])
                if written <= 0:
                    raise OSError("short request record write")
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self._fd)
        return hashlib.sha256(data).hexdigest()

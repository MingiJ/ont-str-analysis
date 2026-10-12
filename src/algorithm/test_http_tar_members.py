from __future__ import annotations

import io
import tarfile
import unittest

try:
    from http_tar_members import BLOCK_SIZE, parse_tar_header
except ImportError:  # pragma: no cover
    from .http_tar_members import BLOCK_SIZE, parse_tar_header


def make_tar() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        directory = tarfile.TarInfo("sample/fast5/")
        directory.type = tarfile.DIRTYPE
        archive.addfile(directory)
        payload = b"raw-signal-placeholder"
        member = tarfile.TarInfo("sample/fast5/batch_001.fast5")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    return buffer.getvalue()


class HttpTarMemberTests(unittest.TestCase):
    def test_parse_header_and_skip_padding(self) -> None:
        archive = make_tar()
        directory = parse_tar_header(archive[:BLOCK_SIZE], 0)
        self.assertIsNotNone(directory)
        assert directory is not None
        self.assertEqual(directory.name, "sample/fast5/")
        self.assertEqual(directory.typeflag, "5")
        self.assertEqual(directory.next_header_offset, BLOCK_SIZE)

        member = parse_tar_header(archive[BLOCK_SIZE : 2 * BLOCK_SIZE], BLOCK_SIZE)
        self.assertIsNotNone(member)
        assert member is not None
        self.assertEqual(member.name, "sample/fast5/batch_001.fast5")
        self.assertEqual(member.size, len(b"raw-signal-placeholder"))
        self.assertEqual(member.data_offset, 2 * BLOCK_SIZE)
        self.assertEqual(member.next_header_offset, 3 * BLOCK_SIZE)

    def test_zero_header_marks_tar_eof(self) -> None:
        self.assertIsNone(parse_tar_header(b"\0" * BLOCK_SIZE, 4096))

    def test_invalid_checksum_is_rejected(self) -> None:
        archive = bytearray(make_tar())
        archive[0] ^= 1
        with self.assertRaisesRegex(ValueError, "invalid tar checksum"):
            parse_tar_header(bytes(archive[:BLOCK_SIZE]), 0)


if __name__ == "__main__":
    unittest.main()

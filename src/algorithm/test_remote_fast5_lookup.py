from __future__ import annotations

import io
import unittest

try:
    from remote_fast5_lookup import HttpSegmentFile, canonical_read_id
except ImportError:  # pragma: no cover
    from .remote_fast5_lookup import HttpSegmentFile, canonical_read_id


class MemoryRangeReader:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self, start: int, size: int) -> bytes:
        return self.payload[start : start + size]


class RemoteFast5LookupTests(unittest.TestCase):
    def test_segment_file_bounds_reads_and_seeks(self) -> None:
        segment = HttpSegmentFile(MemoryRangeReader(b"prefix-DATA-suffix"), 7, 4)
        self.assertEqual(segment.read(2), b"DA")
        self.assertEqual(segment.tell(), 2)
        self.assertEqual(segment.seek(-1, io.SEEK_CUR), 1)
        self.assertEqual(segment.read(), b"ATA")
        self.assertEqual(segment.read(), b"")
        self.assertEqual(segment.seek(-2, io.SEEK_END), 2)
        self.assertEqual(segment.read(10), b"TA")

    def test_canonical_read_id_removes_only_group_prefix(self) -> None:
        self.assertEqual(canonical_read_id("read_abc-def"), "abc-def")
        self.assertEqual(canonical_read_id("abc-def"), "abc-def")


if __name__ == "__main__":
    unittest.main()

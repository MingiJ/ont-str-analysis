from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import h5py

try:
    from extract_external_fast5_reads import canonical_read_id, copy_groups
except ImportError:  # pragma: no cover
    from .extract_external_fast5_reads import canonical_read_id, copy_groups


class ExtractExternalFast5Tests(unittest.TestCase):
    def test_canonical_read_id(self) -> None:
        self.assertEqual(canonical_read_id("read_abc"), "abc")
        self.assertEqual(canonical_read_id("abc"), "abc")

    def test_copy_groups_preserves_multi_fast5_root_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.fast5"
            output = Path(directory) / "selected.fast5"
            with h5py.File(source, "w") as handle:
                handle.attrs["file_type"] = b"multi-read"
                handle.attrs["file_version"] = b"2.2"
                handle.create_group("read_abc")
            copy_groups(output, {"abc": (source, "read_abc")}, overwrite=False)
            with h5py.File(output, "r") as handle:
                self.assertEqual(str(handle.attrs["file_type"]), "multi-read")
                self.assertEqual(str(handle.attrs["file_version"]), "2.2")
                self.assertIn("read_abc", handle)


if __name__ == "__main__":
    unittest.main()

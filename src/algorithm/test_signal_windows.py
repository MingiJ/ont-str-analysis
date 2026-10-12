from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

try:
    from signal_windows import read_fast5_signal
except ImportError:  # pragma: no cover
    from .signal_windows import read_fast5_signal


class SignalWindowsFast5Tests(unittest.TestCase):
    def test_reads_modern_multi_fast5_root_group(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "multi.fast5"
            with h5py.File(path, "w") as handle:
                handle.create_dataset("read_abc/Raw/Signal", data=np.array([1, 2, 3], dtype=np.int16))
            signal = read_fast5_signal(path, "abc")
            np.testing.assert_array_equal(signal, np.array([1, 2, 3], dtype=np.float32))


if __name__ == "__main__":
    unittest.main()

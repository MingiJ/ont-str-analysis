from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

try:
    from external_fast5_batches import candidate_rows, estimate_ranks, load_targets, parse_header
except ImportError:  # pragma: no cover
    from .external_fast5_batches import candidate_rows, estimate_ranks, load_targets, parse_header


class ExternalFast5BatchTests(unittest.TestCase):
    def test_parse_header(self) -> None:
        read_id, start = parse_header(
            "@abc runid=run sampleid=sample start_time=2021-05-04T01:52:00Z"
        )
        self.assertEqual(read_id, "abc")
        self.assertEqual(start, "2021-05-04T01:52:00Z")

    def test_candidate_rows_include_neighboring_batches(self) -> None:
        members = {
            batch: {
                "name": f"run_{batch}.fast5",
                "data_offset": str(batch * 1000),
                "size": "900",
            }
            for batch in range(5)
        }
        rows = candidate_rows(
            {"read": "2021-01-01T00:00:00Z"},
            {"read": 8001},
            members,
            batch_size=4000,
            radius=1,
        )
        self.assertEqual([row["candidate_batch"] for row in rows], [1, 2, 3])
        self.assertEqual([row["batch_distance"] for row in rows], [-1, 0, 1])

    def test_estimate_ranks_counts_lexicographically_preceding_headers(self) -> None:
        targets = {
            "read-b": "2021-01-01T00:00:02Z",
            "read-d": "2021-01-01T00:00:04Z",
        }
        headers = [
            "read-a runid=x start_time=2021-01-01T00:00:01Z\n",
            "read-b runid=x start_time=2021-01-01T00:00:02Z\n",
            "read-c runid=x start_time=2021-01-01T00:00:03Z\n",
            "read-d runid=x start_time=2021-01-01T00:00:04Z\n",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "headers.txt"
            path.write_text("".join(headers))
            self.assertEqual(
                estimate_ranks(targets, [path]),
                {"read-b": 1, "read-d": 3},
            )

    def test_load_targets_recovers_timestamp_from_header_census(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata = Path(directory) / "metadata.tsv"
            headers = Path(directory) / "headers.txt"
            metadata.write_text("read_id\tfastq_comment\nread-b\t\n")
            headers.write_text(
                "read-a runid=x start_time=2021-01-01T00:00:01Z\n"
                "read-b runid=x start_time=2021-01-01T00:00:02Z\n"
            )
            self.assertEqual(
                load_targets(metadata, [headers]),
                {"read-b": "2021-01-01T00:00:02Z"},
            )


if __name__ == "__main__":
    unittest.main()

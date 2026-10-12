#!/usr/bin/env python3
"""Locate selected read IDs in multi-FAST5 members of a remote tar archive.

The tar member index comes from :mod:`http_tar_members`.  Each HDF5 member is
opened through a bounded, seekable HTTP Range view, so only HDF5 metadata is
transferred while searching root ``read_<uuid>`` groups.  No raw signal array
is downloaded during lookup.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import h5py

try:
    from http_tar_members import HttpRangeReader
except ImportError:  # pragma: no cover
    from .http_tar_members import HttpRangeReader


OUTPUT_FIELDS = [
    "read_id",
    "status",
    "root_group",
    "member_name",
    "member_data_offset",
    "member_size",
]


@dataclass(frozen=True)
class IndexedMember:
    name: str
    data_offset: int
    size: int


class HttpSegmentFile(io.RawIOBase):
    """Seekable read-only view of one byte segment in a remote object."""

    def __init__(self, reader: HttpRangeReader, base_offset: int, size: int):
        super().__init__()
        self.reader = reader
        self.base_offset = base_offset
        self.size = size
        self.position = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            position = offset
        elif whence == io.SEEK_CUR:
            position = self.position + offset
        elif whence == io.SEEK_END:
            position = self.size + offset
        else:
            raise ValueError(f"invalid seek mode: {whence}")
        if position < 0:
            raise ValueError("negative seek position")
        self.position = min(position, self.size)
        return self.position

    def read(self, size: int = -1) -> bytes:
        if self.position >= self.size:
            return b""
        if size is None or size < 0:
            size = self.size - self.position
        size = min(size, self.size - self.position)
        payload = self.reader.read(self.base_offset + self.position, size)
        self.position += len(payload)
        return payload

    def readinto(self, buffer: bytearray | memoryview) -> int:
        payload = self.read(len(buffer))
        buffer[: len(payload)] = payload
        return len(payload)


def canonical_read_id(value: str) -> str:
    value = value.strip()
    return value[5:] if value.startswith("read_") else value


def load_read_ids(path: Path) -> set[str]:
    with path.open() as handle:
        read_ids = {
            canonical_read_id(line.split("\t", 1)[0])
            for line in handle
            if line.strip() and not line.startswith("#")
        }
    if not read_ids:
        raise ValueError(f"no read IDs found in {path}")
    return read_ids


def load_members(path: Path) -> list[IndexedMember]:
    members = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row.get("typeflag") not in {"", "0", None}:
                continue
            name = row.get("name", "")
            if not name.endswith(".fast5"):
                continue
            members.append(
                IndexedMember(
                    name=name,
                    data_offset=int(row["data_offset"]),
                    size=int(row["size"]),
                )
            )
    if not members:
        raise ValueError(f"no FAST5 members found in {path}")
    return members


def inspect_member(
    url: str,
    member: IndexedMember,
    targets: frozenset[str],
    chunk_size: int,
    timeout: float,
) -> tuple[IndexedMember, dict[str, str], int, int, str]:
    reader = HttpRangeReader(url, chunk_size=chunk_size, timeout=timeout)
    segment = HttpSegmentFile(reader, member.data_offset, member.size)
    matches: dict[str, str] = {}
    error = ""
    try:
        with h5py.File(segment, "r") as handle:
            for root_group in handle.keys():
                read_id = canonical_read_id(root_group)
                if read_id in targets:
                    matches[read_id] = root_group
    except Exception as exc:  # keep scanning other independent members
        error = f"{type(exc).__name__}: {exc}"
    return member, matches, reader.requests_made, reader.bytes_fetched, error


def locate_reads(
    url: str,
    members: list[IndexedMember],
    targets: set[str],
    *,
    workers: int,
    chunk_size: int,
    timeout: float,
    progress_every: int,
) -> tuple[dict[str, tuple[IndexedMember, str]], dict[str, int]]:
    found: dict[str, tuple[IndexedMember, str]] = {}
    stats = {"members_scanned": 0, "requests_made": 0, "bytes_fetched": 0, "errors": 0}
    frozen_targets = frozenset(targets)
    member_iterator = iter(members)
    in_flight = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for _ in range(min(len(members), workers * 2)):
            member = next(member_iterator, None)
            if member is None:
                break
            future = executor.submit(
                inspect_member, url, member, frozen_targets, chunk_size, timeout
            )
            in_flight[future] = member

        while in_flight:
            completed = next(as_completed(in_flight))
            in_flight.pop(completed)
            member, matches, requests, fetched, error = completed.result()
            stats["members_scanned"] += 1
            stats["requests_made"] += requests
            stats["bytes_fetched"] += fetched
            if error:
                stats["errors"] += 1
                print(f"warning: {member.name}: {error}", file=sys.stderr)
            for read_id, root_group in matches.items():
                found[read_id] = (member, root_group)

            if progress_every and stats["members_scanned"] % progress_every == 0:
                print(
                    f"members={stats['members_scanned']}/{len(members)} "
                    f"found={len(found)}/{len(targets)} requests={stats['requests_made']} "
                    f"bytes={stats['bytes_fetched']}",
                    file=sys.stderr,
                    flush=True,
                )
            if len(found) == len(targets):
                for future in in_flight:
                    future.cancel()
                break

            member = next(member_iterator, None)
            if member is not None:
                future = executor.submit(
                    inspect_member, url, member, frozen_targets, chunk_size, timeout
                )
                in_flight[future] = member
    return found, stats


def write_results(
    path: Path,
    targets: set[str],
    found: dict[str, tuple[IndexedMember, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, delimiter="\t")
        writer.writeheader()
        for read_id in sorted(targets):
            match = found.get(read_id)
            if match is None:
                writer.writerow({"read_id": read_id, "status": "not_found"})
                continue
            member, root_group = match
            writer.writerow(
                {
                    "read_id": read_id,
                    "status": "found",
                    "root_group": root_group,
                    "member_name": member.name,
                    "member_data_offset": member.data_offset,
                    "member_size": member.size,
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--member-index", type=Path, required=True)
    parser.add_argument("--read-ids", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=1048576)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--max-members", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    targets = load_read_ids(args.read_ids)
    members = load_members(args.member_index)
    if args.max_members:
        members = members[: args.max_members]
    found, stats = locate_reads(
        args.url,
        members,
        targets,
        workers=args.workers,
        chunk_size=args.chunk_size,
        timeout=args.timeout,
        progress_every=args.progress_every,
    )
    write_results(args.output, targets, found)
    print(
        f"Wrote {len(found)}/{len(targets)} matches to {args.output}; "
        f"members={stats['members_scanned']} requests={stats['requests_made']} "
        f"bytes={stats['bytes_fetched']} errors={stats['errors']}"
    )


if __name__ == "__main__":
    main()

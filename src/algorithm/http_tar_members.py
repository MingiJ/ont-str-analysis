#!/usr/bin/env python3
"""Index an uncompressed remote tar with small HTTP Range requests.

The SRA raw-signal objects used for external confirmation are 100--293 GB
uncompressed tar archives.  Downloading an entire archive merely to discover
member offsets is unnecessary.  This utility reads each 512-byte tar header,
skips payloads arithmetically, and writes a reproducible member index.  It
refuses servers that ignore Range requests so it cannot accidentally stream a
whole object.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BLOCK_SIZE = 512
INDEX_FIELDS = ["header_offset", "data_offset", "size", "typeflag", "name"]


@dataclass(frozen=True)
class TarMember:
    header_offset: int
    data_offset: int
    size: int
    typeflag: str
    name: str

    @property
    def next_header_offset(self) -> int:
        padded_size = ((self.size + BLOCK_SIZE - 1) // BLOCK_SIZE) * BLOCK_SIZE
        return self.data_offset + padded_size


def _decode_text(value: bytes) -> str:
    return value.split(b"\0", 1)[0].decode("utf-8", errors="surrogateescape")


def _parse_number(value: bytes) -> int:
    if value and value[0] & 0x80:
        unsigned = bytes([value[0] & 0x7F]) + value[1:]
        return int.from_bytes(unsigned, byteorder="big", signed=False)
    stripped = value.rstrip(b"\0 ").lstrip(b" ")
    return 0 if not stripped else int(stripped, 8)


def parse_tar_header(block: bytes, offset: int) -> TarMember | None:
    """Parse and checksum one POSIX tar header; return ``None`` at EOF."""
    if len(block) != BLOCK_SIZE:
        raise ValueError(f"tar header at {offset} has {len(block)} bytes, expected 512")
    if block == b"\0" * BLOCK_SIZE:
        return None

    stored_checksum = _parse_number(block[148:156])
    checksum_block = block[:148] + b" " * 8 + block[156:]
    computed_checksum = sum(checksum_block)
    if stored_checksum != computed_checksum:
        raise ValueError(
            f"invalid tar checksum at byte {offset}: "
            f"stored={stored_checksum}, computed={computed_checksum}"
        )

    name = _decode_text(block[0:100])
    prefix = _decode_text(block[345:500])
    if prefix:
        name = f"{prefix}/{name}"
    typeflag = _decode_text(block[156:157]) or "0"
    size = _parse_number(block[124:136])
    return TarMember(offset, offset + BLOCK_SIZE, size, typeflag, name)


class HttpRangeReader:
    """Small cached HTTP Range reader that rejects non-partial responses."""

    def __init__(self, url: str, *, chunk_size: int = 65536, timeout: float = 60.0):
        if chunk_size < BLOCK_SIZE:
            raise ValueError("chunk_size must be at least 512")
        self.url = url
        self.chunk_size = chunk_size
        self.timeout = timeout
        self._cache_start = -1
        self._cache = b""
        self.total_size: int | None = None
        self.requests_made = 0
        self.bytes_fetched = 0

    def _fetch(self, start: int, end: int) -> bytes:
        request = Request(
            self.url,
            headers={"Range": f"bytes={start}-{end}", "User-Agent": "ont-str-analysis/1.0"},
        )
        try:
            response = urlopen(request, timeout=self.timeout)
        except HTTPError as error:
            raise RuntimeError(f"range request failed at byte {start}: HTTP {error.code}") from error
        with response:
            status = getattr(response, "status", None)
            content_range = response.headers.get("Content-Range", "")
            if status != 206 or not content_range.startswith(f"bytes {start}-"):
                raise RuntimeError(
                    "server ignored or changed the Range request; refusing a possible full download "
                    f"(status={status}, Content-Range={content_range!r})"
                )
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+|\*)", content_range)
            if not match:
                raise RuntimeError(f"unrecognized Content-Range: {content_range!r}")
            if match.group(3) != "*":
                self.total_size = int(match.group(3))
            payload = response.read()
            self.requests_made += 1
            self.bytes_fetched += len(payload)
            return payload

    def read(self, start: int, size: int) -> bytes:
        if size <= 0:
            return b""
        cache_end = self._cache_start + len(self._cache)
        if self._cache_start <= start and start + size <= cache_end:
            relative = start - self._cache_start
            return self._cache[relative : relative + size]

        fetch_size = max(size, self.chunk_size)
        end = start + fetch_size - 1
        if self.total_size is not None:
            end = min(end, self.total_size - 1)
        self._cache = self._fetch(start, end)
        self._cache_start = start
        return self._cache[:size]


def scan_members(
    reader: HttpRangeReader,
    *,
    max_members: int = 0,
    progress_every: int = 100,
) -> list[TarMember]:
    members: list[TarMember] = []
    offset = 0
    pending_long_name: str | None = None
    while True:
        block = reader.read(offset, BLOCK_SIZE)
        member = parse_tar_header(block, offset)
        if member is None:
            break

        if member.typeflag in {"L", "K"}:
            payload = reader.read(member.data_offset, member.size)
            if member.typeflag == "L":
                pending_long_name = _decode_text(payload)
        elif member.typeflag in {"x", "g"}:
            # PAX records only modify the following logical member.  Current
            # SRA archives use ordinary USTAR paths, so retain the record in
            # the index and continue without interpreting optional keys.
            members.append(member)
        else:
            if pending_long_name is not None:
                member = TarMember(
                    member.header_offset,
                    member.data_offset,
                    member.size,
                    member.typeflag,
                    pending_long_name,
                )
                pending_long_name = None
            members.append(member)

        offset = member.next_header_offset
        if progress_every and len(members) % progress_every == 0:
            print(
                f"indexed={len(members)} next_offset={offset} "
                f"object_size={reader.total_size or 'unknown'}",
                file=sys.stderr,
                flush=True,
            )
        if max_members and len(members) >= max_members:
            break
        if reader.total_size is not None and offset >= reader.total_size:
            break
    return members


def write_index(path: Path, members: list[TarMember]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_FIELDS, delimiter="\t")
        writer.writeheader()
        for member in members:
            writer.writerow(
                {
                    "header_offset": member.header_offset,
                    "data_offset": member.data_offset,
                    "size": member.size,
                    "typeflag": member.typeflag,
                    "name": member.name,
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunk-size", type=int, default=65536)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-members", type=int, default=0, help="0 scans to tar EOF")
    parser.add_argument("--progress-every", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reader = HttpRangeReader(args.url, chunk_size=args.chunk_size, timeout=args.timeout)
    members = scan_members(
        reader,
        max_members=args.max_members,
        progress_every=args.progress_every,
    )
    write_index(args.output, members)
    print(f"Wrote {len(members)} members to {args.output}")


if __name__ == "__main__":
    main()

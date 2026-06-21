import json
from pathlib import Path

from mahoun.ledger.storage import FileLedgerWriter


def test_ledger_hash_chain(tmp_path: Path):
    writer = FileLedgerWriter(str(tmp_path))
    h1 = writer.write("evt", "r1", {"a": 1})
    h2 = writer.write("evt", "r2", {"a": 2})
    assert h1 != h2

    day_file = next(tmp_path.glob("*.jsonl"))
    lines = day_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    first_record = json.loads(lines[0])
    second_record = json.loads(lines[1])

    assert second_record["prev_hash"] == first_record["hash"]

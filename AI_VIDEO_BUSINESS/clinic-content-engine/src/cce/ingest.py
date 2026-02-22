from __future__ import annotations

from pathlib import Path

from rich.console import Console

from cce.utils import chunk_text, clean_text, read_source_files, write_jsonl


def run_ingest(client_dir: Path, console: Console) -> None:
    sources_dir = client_dir / "sources"
    if not sources_dir.exists():
        raise FileNotFoundError(f"Missing sources directory: {sources_dir}")

    source_entries = read_source_files(sources_dir)
    if not source_entries:
        raise FileNotFoundError(f"No .txt/.md files found in {sources_dir}")

    chunks: list[dict] = []
    for source_file, raw_text in source_entries:
        normalized = clean_text(raw_text)
        for idx, chunk in enumerate(chunk_text(normalized, chunk_size=1000, overlap=100)):
            chunks.append(
                {
                    "source_file": str(source_file.relative_to(client_dir)),
                    "chunk_id": f"{source_file.stem}-{idx:04d}",
                    "text": chunk,
                }
            )

    kb_dir = client_dir / "kb"
    kb_path = kb_dir / "kb_chunks.jsonl"
    write_jsonl(kb_path, chunks)

    console.print(f"[green]Ingest complete[/green]: {len(source_entries)} source files -> {len(chunks)} chunks")
    console.print(f"[cyan]Wrote[/cyan] {kb_path}")

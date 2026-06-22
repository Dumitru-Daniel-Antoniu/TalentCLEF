from __future__ import annotations

import csv
import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import torch
from tqdm.auto import tqdm
from transformers import MarianMTModel, MarianTokenizer


MODEL_BY_SOURCE_LANGUAGE = {
    "en": "Helsinki-NLP/opus-mt-en-ro",
    "es": "Helsinki-NLP/opus-mt-es-ro",
}

DEFAULT_COLUMNS = ("Resume", "Job Description")

INPUT_CSV = Path("C:\\Users\\ddumi\\Desktop\\Faculty\\MasterSecondYear\\Dissertation\\TalentCLEF\\Data\\A\\Training\\en\\job_applicant_dataset.csv")

SOURCE_LANGUAGE = "en"

OUTPUT_CSV: Path | None = None

RESUME_COLUMN = "Resume"
JOB_DESCRIPTION_COLUMN = "Job Description"

BATCH_SIZE = 16
MAX_SOURCE_TOKENS = 450
MAX_NEW_TOKENS = 512
NUM_BEAMS = 4

DEVICE = "auto"

ROW_LIMIT: int | None = None

CACHE_PATH: Path | None = None

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
URL_RE = re.compile(r"^(?:https?://|www\.)\S+$", re.IGNORECASE)
PHONE_RE = re.compile(r"^\+?[\d\s()./-]{7,}$")
ONLY_STRUCTURE_RE = re.compile(r"^[\W_]+$", re.UNICODE)
BULLET_RE = re.compile(r"^((?:[-•*]|\d+[.)])\s+)(.*)$", re.DOTALL)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

ROMANIAN_DIACRITIC_TRANSLATION = str.maketrans(
    {
        "ş": "ș",
        "Ş": "Ș",
        "ţ": "ț",
        "Ţ": "Ț",
    }
)


@dataclass(frozen=True)
class CellUnit:

    kind: str  # "raw" or "translate"
    raw: str = ""
    prefix: str = ""
    text: str = ""
    trailing_space: str = ""
    line_ending: str = ""




def split_line_ending(raw_line: str) -> tuple[str, str]:
    if raw_line.endswith("\r\n"):
        return raw_line[:-2], "\r\n"
    if raw_line.endswith("\n") or raw_line.endswith("\r"):
        return raw_line[:-1], raw_line[-1]
    return raw_line, ""


def normalize_romanian_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.translate(ROMANIAN_DIACRITIC_TRANSLATION)
    text = re.sub(r"\s*\r?\n\s*", " ", text)
    return text.strip()


def should_preserve_line(text: str) -> bool:
    stripped = text.strip()

    if not stripped:
        return True
    if stripped == "---":
        return True
    if EMAIL_RE.fullmatch(stripped):
        return True
    if URL_RE.fullmatch(stripped):
        return True
    if PHONE_RE.fullmatch(stripped):
        return True
    if ONLY_STRUCTURE_RE.fullmatch(stripped):
        return True

    return False


def iter_cell_units(text: str, column_name: str, resume_column: str) -> Iterator[CellUnit]:
    in_resume_contact_block = column_name == resume_column

    for raw_line in text.splitlines(keepends=True):
        body, line_ending = split_line_ending(raw_line)

        if in_resume_contact_block:
            yield CellUnit(kind="raw", raw=raw_line)
            if body.strip() == "---":
                in_resume_contact_block = False
            continue

        if should_preserve_line(body):
            yield CellUnit(kind="raw", raw=raw_line)
            continue

        leading_match = re.match(r"^\s*", body)
        leading_space = leading_match.group(0) if leading_match else ""
        remainder = body[len(leading_space) :]

        bullet_match = BULLET_RE.match(remainder)
        bullet_prefix = ""
        if bullet_match:
            bullet_prefix = bullet_match.group(1)
            remainder = bullet_match.group(2)

        trailing_match = re.search(r"\s*$", remainder)
        trailing_space = trailing_match.group(0) if trailing_match else ""
        core_text = remainder[: len(remainder) - len(trailing_space)] if trailing_space else remainder

        if not core_text.strip():
            yield CellUnit(kind="raw", raw=raw_line)
            continue

        yield CellUnit(
            kind="translate",
            prefix=leading_space + bullet_prefix,
            text=core_text,
            trailing_space=trailing_space,
            line_ending=line_ending,
        )

    if text == "":
        return


def extract_translatable_segments(
    text: str,
    column_name: str,
    resume_column: str,
) -> Iterator[str]:
    for unit in iter_cell_units(text, column_name, resume_column):
        if unit.kind == "translate":
            yield unit.text


def rebuild_cell(
    text: str,
    column_name: str,
    resume_column: str,
    translations: dict[str, str],
) -> str:
    output_parts: list[str] = []

    for unit in iter_cell_units(text, column_name, resume_column):
        if unit.kind == "raw":
            output_parts.append(unit.raw)
            continue

        translated = translations.get(unit.text)
        if translated is None:
            raise KeyError(f"Missing cached translation for: {unit.text[:100]!r}")

        output_parts.append(
            unit.prefix + translated + unit.trailing_space + unit.line_ending
        )

    result = "".join(output_parts)

    if result.count("\n") != text.count("\n"):
        raise RuntimeError(
            "The translated cell no longer has the same number of line breaks."
        )

    return result


def token_count(tokenizer: MarianTokenizer, text: str) -> int:
    return len(tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"])


def split_oversized_piece_by_words(
    text: str,
    tokenizer: MarianTokenizer,
    max_tokens: int,
) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    current: list[str] = []

    for word in words:
        candidate = " ".join(current + [word])

        if current and token_count(tokenizer, candidate) > max_tokens:
            chunks.append(" ".join(current))
            current = [word]
        else:
            current.append(word)

        # Extremely long strings without spaces are kept as their own unit.
        if len(current) == 1 and token_count(tokenizer, current[0]) > max_tokens:
            chunks.append(current[0])
            current = []

    if current:
        chunks.append(" ".join(current))

    return chunks


def split_text_for_model(
    text: str,
    tokenizer: MarianTokenizer,
    max_tokens: int,
) -> list[str]:
    if token_count(tokenizer, text) <= max_tokens:
        return [text]

    sentences = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
    if not sentences:
        return split_oversized_piece_by_words(text, tokenizer, max_tokens)

    chunks: list[str] = []
    current: list[str] = []

    for sentence in sentences:
        if token_count(tokenizer, sentence) > max_tokens:
            if current:
                chunks.append(" ".join(current))
                current = []
            chunks.extend(
                split_oversized_piece_by_words(sentence, tokenizer, max_tokens)
            )
            continue

        candidate = " ".join(current + [sentence])
        if current and token_count(tokenizer, candidate) > max_tokens:
            chunks.append(" ".join(current))
            current = [sentence]
        else:
            current.append(sentence)

    if current:
        chunks.append(" ".join(current))

    return chunks


class TranslationCache:
    def __init__(self, path: Path, model_name: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.model_name = model_name
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS translations (
                model_name TEXT NOT NULL,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                PRIMARY KEY (model_name, source_text)
            )
            """
        )
        self.connection.commit()

    def existing_sources(self) -> set[str]:
        cursor = self.connection.execute(
            "SELECT source_text FROM translations WHERE model_name = ?",
            (self.model_name,),
        )
        return {row[0] for row in cursor}

    def save_many(self, pairs: Iterable[tuple[str, str]]) -> None:
        self.connection.executemany(
            """
            INSERT OR REPLACE INTO translations
                (model_name, source_text, translated_text)
            VALUES (?, ?, ?)
            """,
            (
                (self.model_name, source, translated)
                for source, translated in pairs
            ),
        )
        self.connection.commit()

    def load_all(self) -> dict[str, str]:
        cursor = self.connection.execute(
            """
            SELECT source_text, translated_text
            FROM translations
            WHERE model_name = ?
            """,
            (self.model_name,),
        )
        return dict(cursor.fetchall())

    def close(self) -> None:
        self.connection.close()


def resolve_device(requested: str) -> torch.device:
    if requested == "cpu":
        return torch.device("cpu")
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested, but no CUDA device is available.")
        return torch.device("cuda")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def translate_model_chunks(
    chunks: Sequence[str],
    tokenizer: MarianTokenizer,
    model: MarianMTModel,
    device: torch.device,
    batch_size: int,
    max_source_tokens: int,
    max_new_tokens: int,
    num_beams: int,
) -> list[str]:
    translated_chunks: list[str] = []

    for start in range(0, len(chunks), batch_size):
        batch = list(chunks[start : start + batch_size])

        encoded = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_source_tokens,
        ).to(device)

        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                max_new_tokens=max_new_tokens,
                num_beams=num_beams,
                early_stopping=(num_beams > 1),
            )

        decoded = tokenizer.batch_decode(
            generated,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        translated_chunks.extend(normalize_romanian_text(item) for item in decoded)

    return translated_chunks


def translate_source_block(
    source_texts: Sequence[str],
    tokenizer: MarianTokenizer,
    model: MarianMTModel,
    device: torch.device,
    batch_size: int,
    max_source_tokens: int,
    max_new_tokens: int,
    num_beams: int,
) -> list[tuple[str, str]]:
    """
    Translate a manageable block of source lines. Long lines are split into
    smaller chunks and then reconstructed on their original single line.
    """
    all_chunks: list[str] = []
    ownership: list[tuple[int, int]] = []

    for source_index, source in enumerate(source_texts):
        pieces = split_text_for_model(source, tokenizer, max_source_tokens)
        start = len(all_chunks)
        all_chunks.extend(pieces)
        ownership.append((start, len(pieces)))

    translated_chunks = translate_model_chunks(
        all_chunks,
        tokenizer,
        model,
        device,
        batch_size,
        max_source_tokens,
        max_new_tokens,
        num_beams,
    )

    results: list[tuple[str, str]] = []
    for source, (start, count) in zip(source_texts, ownership):
        translated = " ".join(translated_chunks[start : start + count]).strip()
        results.append((source, normalize_romanian_text(translated)))

    return results


def iter_rows(
    input_path: Path,
    limit: int | None,
) -> tuple[list[str], Iterator[dict[str, str]]]:
    file_handle = input_path.open("r", encoding="utf-8-sig", newline="")
    reader = csv.DictReader(file_handle)

    if reader.fieldnames is None:
        file_handle.close()
        raise ValueError("The CSV file has no header row.")

    def generator() -> Iterator[dict[str, str]]:
        try:
            for index, row in enumerate(reader):
                if limit is not None and index >= limit:
                    break
                yield row
        finally:
            file_handle.close()

    return list(reader.fieldnames), generator()


def collect_unique_segments(
    input_path: Path,
    columns: Sequence[str],
    resume_column: str,
    limit: int | None,
) -> tuple[list[str], set[str], int]:
    fieldnames, rows = iter_rows(input_path, limit)

    missing = [column for column in columns if column not in fieldnames]
    if missing:
        raise ValueError(
            f"Missing required column(s): {missing}. "
            f"Available columns: {fieldnames}"
        )

    unique_segments: set[str] = set()
    row_count = 0

    for row in tqdm(rows, desc="Scanning CSV rows"):
        row_count += 1
        for column in columns:
            value = row.get(column, "")
            unique_segments.update(
                extract_translatable_segments(value, column, resume_column)
            )

    return fieldnames, unique_segments, row_count


def write_translated_csv(
    input_path: Path,
    output_path: Path,
    fieldnames: Sequence[str],
    columns: Sequence[str],
    resume_column: str,
    translations: dict[str, str],
    limit: int | None,
    expected_rows: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _, rows = iter_rows(input_path, limit)
    written_rows = 0

    with output_path.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
            extrasaction="raise",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()

        for row in tqdm(rows, total=expected_rows, desc="Writing Romanian CSV"):
            original_row = dict(row)

            for column in columns:
                row[column] = rebuild_cell(
                    row.get(column, ""),
                    column,
                    resume_column,
                    translations,
                )

            # Verify that no other column was changed.
            for field in fieldnames:
                if field not in columns and row[field] != original_row[field]:
                    raise RuntimeError(
                        f"Unexpected modification in column {field!r}."
                    )

            writer.writerow(row)
            written_rows += 1

    if written_rows != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows} rows, but wrote {written_rows}."
        )


def resolve_configured_path(path: Path) -> Path:
    """Resolve relative configured paths from the script directory."""
    if path.is_absolute():
        return path.resolve()

    script_directory = Path(__file__).resolve().parent
    return (script_directory / path).resolve()


def main() -> None:
    csv.field_size_limit(sys.maxsize)

    if SOURCE_LANGUAGE not in MODEL_BY_SOURCE_LANGUAGE:
        raise ValueError(
            f"SOURCE_LANGUAGE must be one of "
            f"{sorted(MODEL_BY_SOURCE_LANGUAGE)}, not {SOURCE_LANGUAGE!r}."
        )

    if DEVICE not in {"auto", "cpu", "cuda"}:
        raise ValueError(
            f'DEVICE must be "auto", "cpu", or "cuda", not {DEVICE!r}.'
        )

    if BATCH_SIZE < 1:
        raise ValueError("BATCH_SIZE must be at least 1.")
    if MAX_SOURCE_TOKENS < 1:
        raise ValueError("MAX_SOURCE_TOKENS must be at least 1.")
    if MAX_NEW_TOKENS < 1:
        raise ValueError("MAX_NEW_TOKENS must be at least 1.")
    if NUM_BEAMS < 1:
        raise ValueError("NUM_BEAMS must be at least 1.")
    if ROW_LIMIT is not None and ROW_LIMIT < 1:
        raise ValueError("ROW_LIMIT must be None or a positive integer.")

    input_path = resolve_configured_path(INPUT_CSV)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}\n"
            "Update INPUT_CSV in the CONFIGURATION section."
        )

    output_path = (
        resolve_configured_path(OUTPUT_CSV)
        if OUTPUT_CSV is not None
        else input_path.with_name(f"{input_path.stem}_ro.csv")
    )

    columns = (RESUME_COLUMN, JOB_DESCRIPTION_COLUMN)
    model_name = MODEL_BY_SOURCE_LANGUAGE[SOURCE_LANGUAGE]
    cache_path = (
        resolve_configured_path(CACHE_PATH)
        if CACHE_PATH is not None
        else output_path.with_suffix(".translations.sqlite3")
    )

    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Source language: {SOURCE_LANGUAGE}")
    print(f"Translation model: {model_name}")
    print(f"Cache: {cache_path}")

    fieldnames, unique_segments, row_count = collect_unique_segments(
        input_path=input_path,
        columns=columns,
        resume_column=RESUME_COLUMN,
        limit=ROW_LIMIT,
    )

    print(f"Rows selected: {row_count}")
    print(f"Unique translatable lines: {len(unique_segments)}")

    device = resolve_device(DEVICE)
    print(f"Device: {device}")

    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    model.to(device)
    model.eval()

    cache = TranslationCache(cache_path, model_name)

    try:
        existing = cache.existing_sources()
        pending = sorted(
            (segment for segment in unique_segments if segment not in existing),
            key=len,
        )

        print(f"Already cached: {len(unique_segments) - len(pending)}")
        print(f"Still to translate: {len(pending)}")

        source_block_size = max(BATCH_SIZE * 8, 64)

        progress = tqdm(total=len(pending), desc="Translating unique lines")
        for start in range(0, len(pending), source_block_size):
            source_block = pending[start : start + source_block_size]

            translated_pairs = translate_source_block(
                source_texts=source_block,
                tokenizer=tokenizer,
                model=model,
                device=device,
                batch_size=BATCH_SIZE,
                max_source_tokens=MAX_SOURCE_TOKENS,
                max_new_tokens=MAX_NEW_TOKENS,
                num_beams=NUM_BEAMS,
            )

            cache.save_many(translated_pairs)
            progress.update(len(source_block))

        progress.close()

        translations = cache.load_all()

        missing_after_translation = unique_segments - translations.keys()
        if missing_after_translation:
            raise RuntimeError(
                f"{len(missing_after_translation)} translations are missing."
            )

        write_translated_csv(
            input_path=input_path,
            output_path=output_path,
            fieldnames=fieldnames,
            columns=columns,
            resume_column=RESUME_COLUMN,
            translations=translations,
            limit=ROW_LIMIT,
            expected_rows=row_count,
        )
    finally:
        cache.close()

    print("\nTranslation completed successfully.")
    print(f"Romanian CSV: {output_path}")
    print(
        "Encoding: UTF-8 with BOM. Romanian diacritics are preserved "
        "(ă, â, î, ș, ț)."
    )


if __name__ == "__main__":
    main()

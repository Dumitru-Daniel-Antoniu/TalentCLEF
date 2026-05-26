# ============================================================
# English → Spanish Dataset Translation
# Job Applicant Dataset — Kaggle Notebook
# Translates: Resume, Job Description, Job Roles
# Preserves:  Job Applicant Name, Age, Gender, Race,
#             Ethnicity, Best Match
# ============================================================


# ─── CELL 1: Install dependencies ──────────────────────────
# !pip install -q transformers sentencepiece sacremoses


# ─── CELL 2: Imports ───────────────────────────────────────
import os
import math
import random
import warnings
import pandas as pd
import torch
from transformers import MarianMTModel, MarianTokenizer
from tqdm.auto import tqdm

warnings.filterwarnings("ignore")


# ─── CELL 3: Device setup ──────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")


# ─── CELL 4: Configuration ─────────────────────────────────

# Model
MODEL_NAME = "Helsinki-NLP/opus-mt-en-es"

# Paths — adjust INPUT_PATH to wherever your dataset is on Kaggle
INPUT_PATH  = "/kaggle/input/your-dataset/job_applicant_dataset.csv"
OUTPUT_PATH = "/kaggle/working/job_applicant_dataset_es.csv"
CKPT_PATH   = "/kaggle/working/translation_checkpoint.csv"

# Columns to translate (full document chunking applied to all)
TRANSLATE_COLS = ["Resume", "Job Description", "Job Roles"]

# Columns to preserve exactly as-is
KEEP_COLS = [
    "Job Applicant Name", "Age", "Gender",
    "Race", "Ethnicity", "Best Match"
]

# Translation settings
MAX_CHUNK_TOKENS = 450  # max tokens per chunk, leaving buffer for special tokens
BEAM_SIZE        = 4    # beam search width — higher = better quality, slower


# ─── CELL 5: Load model and tokenizer ──────────────────────
print(f"\nLoading translation model: {MODEL_NAME} …")
tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
model     = MarianMTModel.from_pretrained(MODEL_NAME).to(DEVICE)
model.eval()
print("Model loaded successfully.")
print(f"Vocabulary size: {tokenizer.vocab_size:,}")


# ─── CELL 6: Translation helper functions ──────────────────

def count_tokens(text, tokenizer):
    """
    Count how many subword tokens a string produces.
    Used to decide whether a chunk needs further splitting.
    """
    return len(tokenizer.encode(str(text), truncation=False))


def split_into_chunks(text, tokenizer, max_tokens=MAX_CHUNK_TOKENS):
    """
    Split a document into chunks that each fit within max_tokens.

    Strategy:
      1. Split on newlines first — preserves resume/JD section structure
         (PROFESSIONAL EXPERIENCE, EDUCATION, SKILLS sections, bullet points).
      2. If a single line exceeds max_tokens, fall back to word-level splitting
         so nothing is ever silently truncated.

    Returns a list of string chunks that together reconstruct the full
    document when joined with newline characters.
    """
    if not text or str(text).strip() == "" or str(text) == "nan":
        return [""]

    text  = str(text)
    lines = text.split("\n")

    chunks      = []
    current     = []    # lines accumulated into the current chunk
    current_tok = 0     # token count of the current chunk

    for line in lines:
        line_tok = count_tokens(line, tokenizer)

        # ── Case 1: Single line exceeds the token limit ────────────
        # Can happen with very long summary paragraphs.
        # Flush the current buffer, then split this line by words.
        if line_tok > max_tokens:
            if current:
                chunks.append("\n".join(current))
                current, current_tok = [], 0

            words     = line.split()
            sub_chunk = []
            sub_tok   = 0

            for word in words:
                wt = count_tokens(word, tokenizer)
                if sub_tok + wt > max_tokens and sub_chunk:
                    chunks.append(" ".join(sub_chunk))
                    sub_chunk, sub_tok = [], 0
                sub_chunk.append(word)
                sub_tok += wt

            if sub_chunk:
                chunks.append(" ".join(sub_chunk))

        # ── Case 2: Adding this line would overflow current buffer ──
        elif current_tok + line_tok > max_tokens and current:
            chunks.append("\n".join(current))
            current     = [line]
            current_tok = line_tok

        # ── Case 3: Line fits comfortably in current buffer ─────────
        else:
            current.append(line)
            current_tok += line_tok

    # Flush any remaining lines
    if current:
        chunks.append("\n".join(current))

    return chunks if chunks else [""]


def translate_text_full(text, tokenizer, model):
    """
    Translate a single document in full, regardless of its length.

    Pipeline:
      split_into_chunks() → translate each chunk → rejoin with newline

    The newline join means the translated document retains the same
    section structure as the original (headers, bullet points, etc.).
    """
    if not text or str(text).strip() == "" or str(text) == "nan":
        return ""

    chunks = split_into_chunks(str(text), tokenizer)

    translated_chunks = []
    for chunk in chunks:
        if not chunk.strip():
            translated_chunks.append("")
            continue

        enc = tokenizer(
            [chunk],
            return_tensors = "pt",
            padding        = True,
            truncation     = True,
            max_length     = MAX_CHUNK_TOKENS + 62,   # buffer for special tokens
        ).to(DEVICE)

        with torch.no_grad():
            out = model.generate(
                **enc,
                num_beams      = BEAM_SIZE,
                max_length     = MAX_CHUNK_TOKENS + 62,
                early_stopping = True,
            )

        translated_chunks.append(
            tokenizer.batch_decode(out, skip_special_tokens=True)[0]
        )

    return "\n".join(translated_chunks)


def translate_column_full(series, tokenizer, model, desc="Translating"):
    """
    Translate a full pandas Series using full-document chunked translation.
    Each text is translated independently so chunk boundaries are determined
    by that document's own structure, not by a shared batch padding scheme.
    """
    results = []
    for text in tqdm(series.tolist(), desc=desc):
        results.append(translate_text_full(text, tokenizer, model))
    return results


# ─── CELL 7: Load dataset ──────────────────────────────────
print(f"\nLoading dataset from: {INPUT_PATH}")
df = pd.read_csv(INPUT_PATH)
print(f"Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print(f"\nValue counts (Best Match):\n{df['Best Match'].value_counts()}")
print(f"\nUnique Job Roles: {df['Job Roles'].nunique()}")
print(f"Sample Job Roles: {df['Job Roles'].unique()[:5].tolist()}")

# Verify all expected columns exist
for col in TRANSLATE_COLS + KEEP_COLS:
    assert col in df.columns, f"Column '{col}' not found in dataset!"
print("\nAll expected columns verified.")


# ─── CELL 8: Estimate translation time ─────────────────────
avg_chunks_resume = math.ceil(
    df["Resume"].str.len().mean() / (MAX_CHUNK_TOKENS * 4)
)
avg_chunks_jd = math.ceil(
    df["Job Description"].str.len().mean() / (MAX_CHUNK_TOKENS * 4)
)
# Job Roles are short phrases — always 1 chunk each
total_chunks_est  = len(df) * (avg_chunks_resume + avg_chunks_jd + 1)
secs_per_chunk    = 0.8   # approximate on T4 with beam_size=4

print(f"\nEstimated translation time:")
print(f"  Avg chunks per Resume         : ~{avg_chunks_resume}")
print(f"  Avg chunks per Job Description: ~{avg_chunks_jd}")
print(f"  Total chunks estimated        : ~{total_chunks_est:,}")
print(f"  Estimated total time          : ~{total_chunks_est * secs_per_chunk / 3600:.1f} hours")
print(f"  (Checkpoint saves after every column in case of timeout)")


# ─── CELL 9: Resume from checkpoint if available ───────────
if os.path.exists(CKPT_PATH):
    print(f"\nCheckpoint found at: {CKPT_PATH}")
    print("Resuming from last saved state …")
    df_done      = pd.read_csv(CKPT_PATH)
    start_row    = len(df_done)
    df_remaining = df.iloc[start_row:].reset_index(drop=True).copy()
    print(f"  Already translated : {start_row:,} rows")
    print(f"  Remaining          : {len(df_remaining):,} rows")
else:
    print("\nNo checkpoint found — starting from row 0.")
    df_done      = pd.DataFrame(columns=df.columns)
    df_remaining = df.copy()
    start_row    = 0


# ─── CELL 10: Translate ────────────────────────────────────
if len(df_remaining) == 0:
    print("\nAll rows already translated. Loading checkpoint as final output.")
    df_done = pd.read_csv(CKPT_PATH)
else:
    print(f"\nTranslating {len(df_remaining):,} remaining rows …")
    print("Checkpoint is saved after each column completes.\n")

    for col in TRANSLATE_COLS:
        print(f"\n{'─'*55}")
        print(f"  Column : {col}")
        print(f"{'─'*55}")

        translated = translate_column_full(
            df_remaining[col],
            tokenizer,
            model,
            desc=col,
        )
        df_remaining[col] = translated

        # Save checkpoint after every column so a timeout mid-column
        # only loses that column's progress, not previous columns
        df_checkpoint = pd.concat(
            [df_done, df_remaining], ignore_index=True
        )
        df_checkpoint.to_csv(CKPT_PATH, index=False)
        print(f"  Column '{col}' done. "
              f"Checkpoint saved ({len(df_checkpoint):,} rows total).")

    # Merge newly translated batch with already-completed rows
    df_done = pd.concat([df_done, df_remaining], ignore_index=True)


# ─── CELL 11: Save final output ────────────────────────────
df_done.to_csv(OUTPUT_PATH, index=False)
print(f"\n{'='*60}")
print(f"  Translation complete!")
print(f"  Output saved to : {OUTPUT_PATH}")
print(f"  Final shape     : {df_done.shape}")
print(f"{'='*60}")


# ─── CELL 12: Sanity check ─────────────────────────────────
print("\n─── Sample translations (row 0) ───")
for col in TRANSLATE_COLS:
    print(f"\n[{col}]")
    print(df_done[col].iloc[0][:400])

print("\n─── Preserved columns (must be identical to original) ───")
df_orig = pd.read_csv(INPUT_PATH)
for col in KEEP_COLS:
    match = (df_done[col].astype(str) == df_orig[col].astype(str)).all()
    status = "✓ unchanged" if match else "✗ CHANGED — investigate!"
    print(f"  {col:<30}: {status}")

print("\n─── Label distribution (must match original) ───")
print("Original :")
print(df_orig["Best Match"].value_counts().to_string())
print("Translated:")
print(df_done["Best Match"].value_counts().to_string())

print("\n─── Job Roles: English → Spanish samples ───")
role_pairs = list(zip(
    df_orig["Job Roles"].unique()[:10],
    df_done["Job Roles"].unique()[:10],
))
for orig, trans in role_pairs:
    print(f"  {str(orig):<35} → {trans}")

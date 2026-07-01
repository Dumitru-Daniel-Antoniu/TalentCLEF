import os
import math
import random
import warnings
import pandas as pd
import torch
from transformers import MarianMTModel, MarianTokenizer
from tqdm.auto import tqdm

warnings.filterwarnings("ignore")


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

MODEL_NAME = "Helsinki-NLP/opus-mt-en-es"

INPUT_PATH  = "/kaggle/input/your-dataset/job_applicant_dataset.csv"
OUTPUT_PATH = "/kaggle/working/job_applicant_dataset_es.csv"
CKPT_PATH   = "/kaggle/working/translation_checkpoint.csv"

TRANSLATE_COLS = ["Resume", "Job Description", "Job Roles"]

KEEP_COLS = [
    "Job Applicant Name", "Age", "Gender",
    "Race", "Ethnicity", "Best Match"
]

MAX_CHUNK_TOKENS = 450  
BEAM_SIZE = 4    


print(f"\nLoading translation model: {MODEL_NAME} …")
tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
model     = MarianMTModel.from_pretrained(MODEL_NAME).to(DEVICE)
model.eval()
print("Model loaded successfully.")
print(f"Vocabulary size: {tokenizer.vocab_size:,}")



def count_tokens(text, tokenizer):
    return len(tokenizer.encode(str(text), truncation=False))


def split_into_chunks(text, tokenizer, max_tokens=MAX_CHUNK_TOKENS):
    if not text or str(text).strip() == "" or str(text) == "nan":
        return [""]

    text = str(text)
    lines = text.split("\n")

    chunks = []
    current = []    
    current_tok = 0  

    for line in lines:
        line_tok = count_tokens(line, tokenizer)

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

        elif current_tok + line_tok > max_tokens and current:
            chunks.append("\n".join(current))
            current     = [line]
            current_tok = line_tok

        else:
            current.append(line)
            current_tok += line_tok

    if current:
        chunks.append("\n".join(current))

    return chunks if chunks else [""]


def translate_text_full(text, tokenizer, model):
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
            padding = True,
            truncation = True,
            max_length = MAX_CHUNK_TOKENS + 62
        ).to(DEVICE)

        with torch.no_grad():
            out = model.generate(
                **enc,
                num_beams = BEAM_SIZE,
                max_length = MAX_CHUNK_TOKENS + 62,
                early_stopping = True
            )

        translated_chunks.append(
            tokenizer.batch_decode(out, skip_special_tokens=True)[0]
        )

    return "\n".join(translated_chunks)


def translate_column_full(series, tokenizer, model, desc="Translating"):
    results = []
    for text in tqdm(series.tolist(), desc=desc):
        results.append(translate_text_full(text, tokenizer, model))
    return results


print(f"\nLoading dataset from: {INPUT_PATH}")
df = pd.read_csv(INPUT_PATH)
print(f"Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print(f"\nValue counts (Best Match):\n{df['Best Match'].value_counts()}")
print(f"\nUnique Job Roles: {df['Job Roles'].nunique()}")
print(f"Sample Job Roles: {df['Job Roles'].unique()[:5].tolist()}")

for col in TRANSLATE_COLS + KEEP_COLS:
    assert col in df.columns, f"Column '{col}' not found in dataset!"
print("\nAll expected columns verified.")


avg_chunks_resume = math.ceil(
    df["Resume"].str.len().mean() / (MAX_CHUNK_TOKENS * 4)
)
avg_chunks_jd = math.ceil(
    df["Job Description"].str.len().mean() / (MAX_CHUNK_TOKENS * 4)
)
total_chunks_est = len(df) * (avg_chunks_resume + avg_chunks_jd + 1)
secs_per_chunk = 0.8  

print(f"\nEstimated translation time:")
print(f"  Avg chunks per Resume         : ~{avg_chunks_resume}")
print(f"  Avg chunks per Job Description: ~{avg_chunks_jd}")
print(f"  Total chunks estimated        : ~{total_chunks_est:,}")
print(f"  Estimated total time          : ~{total_chunks_est * secs_per_chunk / 3600:.1f} hours")
print(f"  (Checkpoint saves after every column in case of timeout)")


if os.path.exists(CKPT_PATH):
    print(f"\nCheckpoint found at: {CKPT_PATH}")
    print("Resuming from last saved state …")
    df_done = pd.read_csv(CKPT_PATH)
    start_row = len(df_done)
    df_remaining = df.iloc[start_row:].reset_index(drop=True).copy()
    print(f"  Already translated : {start_row:,} rows")
    print(f"  Remaining          : {len(df_remaining):,} rows")
else:
    print("\nNo checkpoint found — starting from row 0.")
    df_done = pd.DataFrame(columns=df.columns)
    df_remaining = df.copy()
    start_row = 0


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
            desc=col
        )
        df_remaining[col] = translated

        df_checkpoint = pd.concat(
            [df_done, df_remaining], ignore_index=True
        )
        df_checkpoint.to_csv(CKPT_PATH, index=False)
        print(f"  Column '{col}' done. "
              f"Checkpoint saved ({len(df_checkpoint):,} rows total).")

    df_done = pd.concat([df_done, df_remaining], ignore_index=True)


df_done.to_csv(OUTPUT_PATH, index=False)
print(f"\n{'='*60}")
print(f"  Translation complete!")
print(f"  Output saved to : {OUTPUT_PATH}")
print(f"  Final shape     : {df_done.shape}")
print(f"{'='*60}")


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

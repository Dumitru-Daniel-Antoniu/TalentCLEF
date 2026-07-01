import re


def clean_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\r", "\n")
    t = re.sub(r"\n{2,}", "\n\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def extract_skills(text: str):
    if not text:
        return set()

    heading_pat = (
        r"(?is)(?:^|\n)\s*(?:skills|required skills|habilidades|competencias|destrezas)"
        r"\s*[:\-\n]+(.*?)(?:\n\s*\n|\n---|$)"
    )
    m = re.search(heading_pat, text)
    block = None
    if m:
        block = m.group(1)
    else:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.search(r"(?i)^\s*(skills|required skills|habilidades|competencias)\b", line):
                block = "\n".join(lines[i + 1 : i + 8])
                break

    if not block:
        tokens = set()
        for token in re.split(r"[\n,•\-\t]+", text[:2000]):
            s = token.strip().lower()
            if 2 <= len(s) <= 40 and len(s.split()) <= 4:
                tokens.add(s)
        return tokens

    parts = re.split(r"[\n,•\-\t]+", block)
    tokens = set()
    for p in parts:
        s = p.strip()
        s = re.sub(r"[^\w &/+-]+$", "", s)
        s = re.sub(r"^[^\w]+", "", s)
        s = " ".join(s.split()).lower()
        if len(s) > 1:
            tokens.add(s)
    return tokens


def summarize_text(text: str, max_words: int = 40) -> str:
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."

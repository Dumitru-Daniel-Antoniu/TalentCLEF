from pathlib import Path
import re
import shutil
import zipfile

import matplotlib.pyplot as plt
import pandas as pd


ZIP_PATH = Path("Development.zip")
EXTRACT_DIR = Path("Development_unzipped")
OUTPUT_DIR = Path("development_eda_outputs")


FEMALE_ASSOCIATED_NAMES = {
    "Abeba", "Agnieszka", "Almaz", "Amara", "Amelia", "Aminata",
    "Amira", "Amélie", "Anahita", "Anastasia", "Anete", "Anita",
    "Anjali", "Annika", "Ayesha", "Aïssatou", "Catalina", "Chioma",
    "Chisom", "Ekaterina", "Eleanor", "Emma", "Fatima", "Giulia",
    "Ingrid", "Irina", "Isabelle", "Jessica", "Ji", "Karin",
    "Katarzyna", "Katerina", "Katharina", "Konstantina", "Kristīne",
    "Layla", "Leilani", "Maja", "Maria", "Mariana", "Marieke",
    "María", "Melissa", "Nur", "Nurul", "Priya", "Radhika", "Rania",
    "Sarah", "Sereina", "Siriporn", "Siti", "Sophia", "Talofa",
    "Thandi", "Valentina", "Yuki",
}

MALE_ASSOCIATED_NAMES = {
    "Abdelrahman", "Abebe", "Abubakar", "Ade", "Adekunle", "Ahmed",
    "Amadou", "Amir", "Andris", "Arjun", "Budi", "Carlos", "Chen",
    "Chukwu", "Cristóbal", "Diego", "Dimitrios", "Dmitri", "Erik",
    "Faamatai", "Faamoana", "Fahad", "Faisal", "James", "Jorn",
    "João", "Jānis", "Kamau", "Karim", "Kenji", "Khalid", "Klaus",
    "Knut", "Kofi", "Kristian", "Maarten", "Mamadou", "Marc", "Marco",
    "Marcus", "Maroun", "Marwan", "Mateo", "Matthias", "Michel", "Min",
    "Moussa", "Muhammad", "Niran", "Pierre", "Pieter", "Piotr",
    "Rajesh", "Ravi", "Reza", "Ricardo", "Sione", "Sitiveni", "Sombat",
    "Somchai", "Soren", "Takeshi", "Thabo", "Tran", "Vakailevu", "Wei",
}


def find_development_root(extract_dir: Path) -> Path:
    """Find the directory that directly contains the English and Spanish folders."""
    candidates = [extract_dir] + [p for p in extract_dir.rglob("*") if p.is_dir()]
    for candidate in candidates:
        if (
            (candidate / "en" / "queries").is_dir()
            and (candidate / "en" / "corpus").is_dir()
        ):
            return candidate
    raise FileNotFoundError(
        "Could not find the Development/en/queries and "
        "Development/en/corpus folders."
    )


def clean_job_title(text: str) -> str:
    """Use the first non-empty line as the title."""
    first_line = next(
        (line.strip() for line in text.splitlines() if line.strip()),
        "Unknown job",
    )
    if first_line.startswith("We are seeking a Paralegal"):
        return "Paralegal, Privacy and Information Management"
    return first_line


SECTION_HEADINGS = {
    "PROFESSIONAL EXPERIENCE",
    "WORK EXPERIENCE",
    "WORK HISTORY",
    "EDUCATION",
    "ACADEMIC BACKGROUND",
    "SKILLS",
    "TECHNICAL SKILLS",
    "CORE COMPETENCIES",
    "PROFESSIONAL SKILLS",
    "CERTIFICATIONS",
    "CERTIFICATIONS & TRAINING",
    "CERTIFICATES",
    "CERTIFICATIONS & LICENSES",
    "PROFESSIONAL CERTIFICATIONS",
    "CERTIFICATIONS & PROFESSIONAL DEVELOPMENT",
    "LANGUAGES",
    "PROFESSIONAL AFFILIATIONS",
    "ADDITIONAL INFORMATION",
    "HOBBIES",
    "ACHIEVEMENTS",
    "PROFESSIONAL ACHIEVEMENTS",
    "REFERENCES",
    "PROFESSIONAL DEVELOPMENT",
    "PROJECTS",
    "OTHER INFORMATION",
    "ACCOMPLISHMENTS",
    "ADDITIONAL SKILLS",
    "PROFESSIONAL ACTIVITIES",
    "AWARDS",
    "TECHNICAL PROFICIENCIES",
    "ADDITIONAL INTERESTS",
}


def normalize_heading(line: str) -> str:
    return line.strip().strip("-").strip().upper()


def extract_section(text: str, possible_starts: set[str]) -> str:
    """Extract text between a selected heading and the following known heading."""
    lines = text.splitlines()
    start_index = None

    for index, line in enumerate(lines):
        if normalize_heading(line) in possible_starts:
            start_index = index + 1
            break

    if start_index is None:
        return ""

    selected_lines = []
    for line in lines[start_index:]:
        if normalize_heading(line) in SECTION_HEADINGS:
            break
        selected_lines.append(line)

    return "\n".join(selected_lines)


def highest_education_level(text: str) -> str:
    education = extract_section(
        text,
        {"EDUCATION", "ACADEMIC BACKGROUND"},
    ).lower()

    if re.search(r"\b(ph\.?d\.?|doctorate|doctoral|doctor of)\b", education):
        return "Doctorate"
    if re.search(
        r"\b(master(?:'s)?|master of|m\.?sc\.?|m\.?a\.?|mba|m\.eng)\b",
        education,
    ):
        return "Master's"
    if re.search(
        r"\b(bachelor(?:'s)?|bachelor of|b\.?sc\.?|b\.?a\.?|b\.eng|bba)\b",
        education,
    ):
        return "Bachelor's"
    if re.search(r"\b(associate(?:'s)?|associate of)\b", education):
        return "Associate"
    if re.search(r"\b(high school|secondary school|ged)\b", education):
        return "High school"
    if re.search(r"\b(diploma|certificate)\b", education):
        return "Diploma/certificate"
    return "Not identified"


MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|"
    r"Sept|Oct|Nov|Dec)"
)
MONTH_DATE_RANGE = re.compile(
    rf"(?i)\b{MONTH}\s+\d{{4}}\s*[–—-]\s*"
    rf"(?:Present|Current|{MONTH}\s+\d{{4}})\b"
)
YEAR_DATE_RANGE = re.compile(
    r"(?i)\b(?:19|20)\d{2}\s*[–—-]\s*"
    r"(?:Present|Current|(?:19|20)\d{2})\b"
)


def count_professional_positions(text: str) -> int:
    experience = extract_section(
        text,
        {"PROFESSIONAL EXPERIENCE", "WORK EXPERIENCE", "WORK HISTORY"},
    )
    return (
        sum(1 for _ in MONTH_DATE_RANGE.finditer(experience))
        + sum(1 for _ in YEAR_DATE_RANGE.finditer(experience))
    )


def binary_name_category(full_name: str) -> str:
    """
    Assign one of two name-associated categories.

    The classification is based on the first name and is intended only
    for an aggregate descriptive graphic. It must not be interpreted as
    verified or self-identified gender.
    """
    first_name = re.split(r"[\s-]+", full_name.strip())[0]

    if first_name in FEMALE_ASSOCIATED_NAMES:
        return "Female"
    if first_name in MALE_ASSOCIATED_NAMES:
        return "Male"

    raise ValueError(
        f"The first name {first_name!r} is not present in the manual mapping. "
        "Add it to one of the two name sets before continuing."
    )


def main() -> None:
    if not ZIP_PATH.exists():
        raise FileNotFoundError(
            f"{ZIP_PATH} was not found. "
            "Place this script next to Development.zip."
        )

    if EXTRACT_DIR.exists():
        shutil.rmtree(EXTRACT_DIR)

    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        archive.extractall(EXTRACT_DIR)

    root = find_development_root(EXTRACT_DIR)
    en_root = root / "en"
    OUTPUT_DIR.mkdir(exist_ok=True)

    # The qrels TSV is the source of the relevance relationships.
    qrels = pd.read_csv(
        en_root / "qrels.tsv",
        sep="\t",
        header=None,
        names=["query_id", "iteration", "corpus_id", "relevance"],
        dtype={"query_id": str, "corpus_id": str},
    )

    positive_qrels = qrels[qrels["relevance"] > 0].copy()

    job_titles = {}
    for path in (en_root / "queries").iterdir():
        text = path.read_text(encoding="utf-8", errors="replace")
        job_titles[path.name] = clean_job_title(text)

    relevant_counts = positive_qrels.groupby("query_id").size().sort_values()
    labels = [job_titles[query_id] for query_id in relevant_counts.index]

    plt.figure(figsize=(10, 6))
    plt.barh(labels, relevant_counts.values)
    plt.xlabel("Number of relevant resumes")
    plt.ylabel("Job description")
    plt.tight_layout()
    jobs_figure = OUTPUT_DIR / "development_jobs_distribution.png"
    plt.savefig(jobs_figure, dpi=300, bbox_inches="tight")
    plt.close()

    resume_rows = []

    for path in sorted(
        (en_root / "corpus").iterdir(),
        key=lambda item: int(item.name),
    ):
        text = path.read_text(encoding="utf-8", errors="replace")
        name = next(
            (line.strip() for line in text.splitlines() if line.strip()),
            "",
        )

        resume_rows.append(
            {
                "resume_id": path.name,
                "name": name,
                "name_based_gender": binary_name_category(name),
                "highest_education": highest_education_level(text),
                "professional_positions": count_professional_positions(text),
            }
        )

    resumes = pd.DataFrame(resume_rows)

    gender_order = ["Female", "Male"]
    gender_counts = (
        resumes["name_based_gender"]
        .value_counts()
        .reindex(gender_order, fill_value=0)
    )

    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(gender_counts.index, gender_counts.values)
    plt.ylabel("Number of resume files")

    total = int(gender_counts.sum())
    for bar, value in zip(bars, gender_counts.values):
        percentage = 100 * value / total
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            value + 4,
            f"{value}\n({percentage:.1f}%)",
            ha="center",
            va="bottom",
        )

    plt.ylim(0, max(gender_counts.values) * 1.18)
    plt.tight_layout()
    gender_figure = OUTPUT_DIR / "development_gender_distribution_binary.png"
    plt.savefig(gender_figure, dpi=300, bbox_inches="tight")
    plt.close()

    education_counts = resumes["highest_education"].value_counts()
    position_counts = (
        resumes["professional_positions"].value_counts().sort_index()
    )

    print("\nGENERAL STRUCTURE")
    print(f"Job descriptions: {len(job_titles)}")
    print(f"Resumes: {len(resumes)}")
    print(f"Positive qrels relationships: {len(positive_qrels)}")
    print(f"Possible query-resume pairs: {len(job_titles) * len(resumes)}")

    print("\nRELEVANT RESUMES PER JOB")
    for query_id, count in relevant_counts.sort_values(
        ascending=False
    ).items():
        print(f"{job_titles[query_id]}: {count}")

    print("\nBINARY NAME-BASED GENDER ESTIMATE")
    print(gender_counts.to_string())
    print(
        f"Female-associated names: "
        f"{100 * gender_counts['Female'] / total:.1f}%"
    )
    print(
        f"Male-associated names: "
        f"{100 * gender_counts['Male'] / total:.1f}%"
    )

    print("\nHIGHEST IDENTIFIED EDUCATION LEVEL")
    print(education_counts.to_string())

    print("\nNUMBER OF LISTED PROFESSIONAL POSITIONS")
    print(position_counts.to_string())
    print(f"Mean: {resumes['professional_positions'].mean():.2f}")
    print(f"Median: {resumes['professional_positions'].median():.0f}")

    summary_path = OUTPUT_DIR / "development_candidate_summary.csv"
    resumes.to_csv(summary_path, index=False)

    print("\nFILES CREATED")
    print(jobs_figure)
    print(gender_figure)
    print(summary_path)


if __name__ == "__main__":
    main()

from pathlib import Path
import re

import matplotlib.pyplot as plt
import pandas as pd


CSV_PATH = Path("job_applicant_dataset.csv")
OUTPUT_DIR = Path("training_eda_outputs")


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

    lines = str(text).splitlines()
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

    if re.search(
        r"\b(ph\.?d\.?|doctorate|doctoral|doctor of|juris doctor|\bjd\b)\b",
        education,
    ):
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

    return "Not identified"


MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
)

DATE_LINE = re.compile(
    rf"(?i)^\s*(?:{MONTH}\s+)?(?:19|20)\d{{2}}\s*[–—-]\s*"
    rf"(?:Present|Current|(?:{MONTH}\s+)?(?:19|20)\d{{2}})\s*$"
)


def count_professional_positions(text: str) -> int:
    experience = extract_section(
        text,
        {"PROFESSIONAL EXPERIENCE", "WORK EXPERIENCE", "WORK HISTORY"},
    )
    return sum(
        bool(DATE_LINE.match(line.strip()))
        for line in experience.splitlines()
    )


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            "job_applicant_dataset.csv was not found. "
            "Place this script in the same directory as the CSV file."
        )

    OUTPUT_DIR.mkdir(exist_ok=True)

    data = pd.read_csv(CSV_PATH)

    required_columns = {
        "Job Applicant Name",
        "Gender",
        "Resume",
        "Job Roles",
        "Best Match",
    }
    missing_columns = required_columns - set(data.columns)

    if missing_columns:
        raise ValueError(
            f"The following required columns are missing: "
            f"{sorted(missing_columns)}"
        )




    top_jobs = data["Job Roles"].value_counts().head(10).sort_values()

    plt.figure(figsize=(10, 6))
    bars = plt.barh(top_jobs.index, top_jobs.values)
    plt.xlabel("Number of training samples")
    plt.ylabel("Job role")

    for bar, value in zip(bars, top_jobs.values):
        plt.text(
            value + 1,
            bar.get_y() + bar.get_height() / 2,
            str(value),
            va="center",
        )

    plt.xlim(0, top_jobs.max() + 25)
    plt.tight_layout()

    jobs_figure = OUTPUT_DIR / "training_top_10_job_roles.png"
    plt.savefig(jobs_figure, dpi=300, bbox_inches="tight")
    plt.close()




    gender_counts = (
        data["Gender"]
        .value_counts()
        .reindex(["Female", "Male"], fill_value=0)
    )

    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(gender_counts.index, gender_counts.values)
    plt.ylabel("Number of training samples")

    total = int(gender_counts.sum())
    for bar, value in zip(bars, gender_counts.values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            value + 70,
            f"{value}\n({100 * value / total:.1f}%)",
            ha="center",
            va="bottom",
        )

    plt.ylim(0, gender_counts.max() * 1.12)
    plt.tight_layout()

    gender_figure = OUTPUT_DIR / "training_gender_distribution.png"
    plt.savefig(gender_figure, dpi=300, bbox_inches="tight")
    plt.close()




    education = data["Resume"].map(highest_education_level)
    positions = data["Resume"].map(count_professional_positions)

    summary = pd.DataFrame(
        {
            "applicant_name": data["Job Applicant Name"],
            "gender": data["Gender"],
            "job_role": data["Job Roles"],
            "best_match": data["Best Match"],
            "highest_education": education,
            "professional_positions": positions,
        }
    )

    summary_path = OUTPUT_DIR / "training_candidate_summary.csv"
    summary.to_csv(summary_path, index=False)

    print("\nGENERAL STRUCTURE")
    print(f"Training samples: {len(data)}")
    print(f"Unique applicant names: {data['Job Applicant Name'].nunique()}")
    print(f"Unique job roles: {data['Job Roles'].nunique()}")

    print("\nGENDER DISTRIBUTION")
    print(gender_counts.to_string())

    print("\nTEN MOST REPRESENTED JOB ROLES")
    print(
        data["Job Roles"]
        .value_counts()
        .head(10)
        .to_string()
    )

    print("\nHIGHEST IDENTIFIED EDUCATION LEVEL")
    print(education.value_counts().to_string())

    print("\nNUMBER OF LISTED PROFESSIONAL POSITIONS")
    print(positions.value_counts().sort_index().to_string())
    print(f"Mean: {positions.mean():.2f}")
    print(f"Median: {positions.median():.0f}")

    print("\nFILES CREATED")
    print(jobs_figure)
    print(gender_figure)
    print(summary_path)


if __name__ == "__main__":
    main()

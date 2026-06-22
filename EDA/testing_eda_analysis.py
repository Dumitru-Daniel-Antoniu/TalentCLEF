from pathlib import Path
import re
import shutil
import zipfile
from collections import Counter

import matplotlib.pyplot as plt
import pandas as pd


ZIP_PATH = Path("Testing.zip")
EXTRACT_DIR = Path("Testing_unzipped")
OUTPUT_DIR = Path("testing_eda_outputs")


def find_testing_root(extract_dir: Path) -> Path:
    candidates = [extract_dir] + [p for p in extract_dir.rglob("*") if p.is_dir()]
    for candidate in candidates:
        if (
            (candidate / "en" / "queries").is_dir()
            and (candidate / "en" / "corpus").is_dir()
            and (candidate / "es" / "queries").is_dir()
            and (candidate / "es" / "corpus").is_dir()
        ):
            return candidate
    raise FileNotFoundError("The English and Spanish testing folders were not found.")


def clean_job_title(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    first = lines[0]

    if first.startswith("We are seeking a Student Success Advisor"):
        return "Student Success Advisor"
    if first.startswith("Position: "):
        return first.split("Position: ", 1)[1]
    if first.startswith("Job Title: "):
        return first.split("Job Title: ", 1)[1]
    if first == "Overview":
        return "Client Success Specialist"
    if first.startswith("We are seeking a Reporting and Insights Manager"):
        return "Reporting and Insights Manager"
    return first


DOMAIN_BY_TITLE = {
    "Test Development Engineer": "Technology and engineering",
    "Security Infrastructure Engineer": "Technology and engineering",
    "Metal Applications Engineer": "Technology and engineering",
    "Senior Software Developer": "Technology and engineering",
    "Product Development Engineer": "Technology and engineering",
    "Enterprise Security Architect": "Technology and engineering",
    "Property Systems Specialist": "Technology and engineering",
    "Lead Systems Programmer": "Technology and engineering",
    "Senior Data Systems Architect": "Technology and engineering",
    "Systems Analyst": "Technology and engineering",
    "Head of Technology for Dental Solutions": "Technology and engineering",
    "Infrastructure Developer": "Technology and engineering",
    "Building Systems Technician": "Technology and engineering",
    "Building Evaluation Intern": "Technology and engineering",
    "Equipment Testing Technician II": "Technology and engineering",

    "Distribution Center Worker": "Business operations and project management",
    "Project Delivery Lead": "Business operations and project management",
    "Reporting and Insights Manager": "Business operations and project management",
    "Logistics Handler": "Business operations and project management",
    "Capacity Planning Manager, EMEA": "Business operations and project management",
    "Principal Project Director": "Business operations and project management",
    "Site Supervisor": "Business operations and project management",

    "Senior Investment Analyst": "Finance and investment",
    "Senior Product Finance Analyst": "Finance and investment",
    "Associate Manager, Alternative Assets Audit": "Finance and investment",
    "Research Scientist - Wholesale Market Making": "Finance and investment",
    "Principal Financial Risk Analyst": "Finance and investment",
    "Investment Operations Analyst": "Finance and investment",

    "Senior Biostatistician, Cancer Research": "Healthcare and regulatory",
    "Senior Field Medical Affairs Manager – Immunology": "Healthcare and regulatory",
    "Regulatory Compliance Specialist": "Healthcare and regulatory",
    "Healthcare Product Registration Specialist": "Healthcare and regulatory",
    "Principal Clinical Investigator, Medical Technology": "Healthcare and regulatory",
    "Senior Regulatory Affairs Quality Officer": "Healthcare and regulatory",

    "Student Success Advisor": "Education, HR and client services",
    "Talent Development Partner": "Education, HR and client services",
    "Human Resources Generalist": "Education, HR and client services",
    "Enrollment Services Coordinator": "Education, HR and client services",
    "Client Success Specialist": "Education, HR and client services",

    "Territory Sales Manager": "Sales and commercial",
}


FEMALE_FIRST_NAMES = {
    "Abeba", "Agnieszka", "Aisha", "Alessandra", "Almaz", "Amahle", "Amelia",
    "Aminata", "Amira", "Amélie", "Anahita", "Anita", "Anjali", "Aolani",
    "Asha", "Ayesha", "Aïssatou", "CAROLINA", "Camille", "Catalina", "Chioma",
    "Chisom", "Ekaterina", "Eleanor", "Emma", "Faaiva", "Farida", "Fatima",
    "Fatou", "Giulia", "Ingrid", "Isabelle", "Ji", "Katarzyna", "Katerina",
    "Katharina", "Katrin", "Kim", "Kristina", "Kristīne", "Layla", "Linh",
    "Magdalena", "Maja", "Malia", "Maria", "Mariana", "Marianne", "Marieke",
    "Mariela", "Marta", "María", "Mei", "Melissa", "Nasrin", "Priya", "Rebecca",
    "Rima", "Sarah", "Sarina", "Siriporn", "Siti", "Sophia", "Thandi", "Yasmin",
    "Yuki",
}

MALE_FIRST_NAMES = {
    "Abdelrahman", "Abdulrahman", "Abebe", "Ade", "Adekunle", "Ahmed", "Alhaji",
    "Amadou", "Amir", "Andrejs", "Arturs", "Budi", "Carlos", "Chen", "Chukwu",
    "Cristóbal", "Dimitrios", "Dimitris", "Dmitri", "Erik", "Faamuina", "Faisal",
    "Hiroshi", "Ismail", "James", "Jamesai", "Jeremiah", "João", "Kamau", "Karim",
    "Khalid", "Klaus", "Knut", "Kofi", "Kristian", "Luc", "Maarten", "Marc",
    "Marco", "Marcus", "Martín", "Marwan", "Michael", "Min", "Muhammad", "Nuno",
    "Pieter", "Piotr", "Rajesh", "Ravi", "Reza", "Ricardo", "Rodrigo", "Sairish",
    "Sanjay", "Sione", "Somchai", "Talanoa", "Thabo", "Wei",
}

FEMALE_FULL_NAMES = {
    "Amara Njeri",
    "Nguyen Thi Linh",
    "Park Ji-woo",
    "Tran Linh",
}

MALE_FULL_NAMES = {
    "Amara Conteh",
    "Amara Jallah",
    "Amara Kipchoge",
    "Amara Kobbah",
    "Amara Koroma",
    "Amara Okonkwo",
    "Amara Sesay",
    "Amara Weah",
    "Park Min-jun",
    "Tran Minh Duc",
}


SECTION_HEADINGS = {
    "PROFESSIONAL EXPERIENCE", "WORK EXPERIENCE", "WORK HISTORY", "EDUCATION",
    "ACADEMIC BACKGROUND", "SKILLS", "TECHNICAL SKILLS", "CORE COMPETENCIES",
    "PROFESSIONAL SKILLS", "CERTIFICATIONS", "CERTIFICATIONS & TRAINING",
    "CERTIFICATES", "CERTIFICATIONS & LICENSES", "PROFESSIONAL CERTIFICATIONS",
    "CERTIFICATIONS & PROFESSIONAL DEVELOPMENT", "LANGUAGES",
    "PROFESSIONAL AFFILIATIONS", "ADDITIONAL INFORMATION", "HOBBIES",
    "ACHIEVEMENTS", "PROFESSIONAL ACHIEVEMENTS", "REFERENCES",
    "PROFESSIONAL DEVELOPMENT", "PROJECTS", "OTHER INFORMATION",
    "ACCOMPLISHMENTS", "ADDITIONAL SKILLS", "PROFESSIONAL ACTIVITIES", "AWARDS",
    "TECHNICAL PROFICIENCIES", "ADDITIONAL INTERESTS",
}


def normalize_heading(line: str) -> str:
    return line.strip().strip("-").strip().upper()


def extract_section(text: str, starts: set[str]) -> str:
    lines = text.splitlines()
    start_index = None

    for index, line in enumerate(lines):
        if normalize_heading(line) in starts:
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
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
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


def classify_name(full_name: str) -> str:
    first_name = re.split(r"[\s-]+", full_name.strip())[0]

    if full_name in FEMALE_FULL_NAMES:
        return "Female"
    if full_name in MALE_FULL_NAMES:
        return "Male"
    if first_name in FEMALE_FIRST_NAMES:
        return "Female"
    if first_name in MALE_FIRST_NAMES:
        return "Male"

    raise ValueError(
        f"The name {full_name!r} is not included in the manual mapping."
    )


def email_multiset(root: Path, language: str) -> Counter:
    email_pattern = re.compile(r"[\w.\-]+@[\w.\-]+\.\w+")
    emails = []

    for path in (root / language / "corpus").iterdir():
        text = path.read_text(encoding="utf-8", errors="replace")
        found = email_pattern.findall(text)

        if not found:
            raise ValueError(f"No email address was found in {path}.")

        emails.append(found[0])

    return Counter(emails)


def main() -> None:
    if not ZIP_PATH.exists():
        raise FileNotFoundError(
            "Testing.zip was not found. Place this script in the same "
            "directory as the archive."
        )

    if EXTRACT_DIR.exists():
        shutil.rmtree(EXTRACT_DIR)

    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        archive.extractall(EXTRACT_DIR)

    root = find_testing_root(EXTRACT_DIR)
    output_dir = OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)

    job_titles = {}
    for path in sorted(
        (root / "en" / "queries").iterdir(),
        key=lambda item: int(item.name),
    ):
        text = path.read_text(encoding="utf-8", errors="replace")
        job_titles[path.name] = clean_job_title(text)

    missing_titles = sorted(set(job_titles.values()) - set(DOMAIN_BY_TITLE))
    if missing_titles:
        raise ValueError(
            f"The following job titles do not have a domain: {missing_titles}"
        )

    domain_counts = pd.Series(
        [DOMAIN_BY_TITLE[title] for title in job_titles.values()]
    ).value_counts().sort_values()

    plt.figure(figsize=(10, 5.5))
    bars = plt.barh(domain_counts.index, domain_counts.values)
    plt.xlabel("Number of job descriptions")
    plt.ylabel("General domain")

    for bar, value in zip(bars, domain_counts.values):
        plt.text(
            value + 0.15,
            bar.get_y() + bar.get_height() / 2,
            str(value),
            va="center",
        )

    plt.xlim(0, domain_counts.max() + 2)
    plt.tight_layout()

    domain_figure = output_dir / "testing_job_domain_distribution.png"
    plt.savefig(domain_figure, dpi=300, bbox_inches="tight")
    plt.close()

    resume_rows = []
    for path in sorted(
        (root / "en" / "corpus").iterdir(),
        key=lambda item: int(item.name),
    ):
        text = path.read_text(encoding="utf-8", errors="replace")
        name = next(
            line.strip()
            for line in text.splitlines()
            if line.strip()
        )

        resume_rows.append(
            {
                "resume_id": path.name,
                "name": name,
                "name_based_gender": classify_name(name),
                "highest_education": highest_education_level(text),
                "professional_positions": count_professional_positions(text),
            }
        )

    resumes = pd.DataFrame(resume_rows)

    gender_counts = (
        resumes["name_based_gender"]
        .value_counts()
        .reindex(["Female", "Male"], fill_value=0)
    )

    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(gender_counts.index, gender_counts.values)
    plt.ylabel("Number of resume files")

    total = int(gender_counts.sum())
    for bar, value in zip(bars, gender_counts.values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            value + 4,
            f"{value}\n({100 * value / total:.1f}%)",
            ha="center",
            va="bottom",
        )

    plt.ylim(0, max(gender_counts.values) * 1.18)
    plt.tight_layout()

    gender_figure = output_dir / "testing_gender_distribution.png"
    plt.savefig(gender_figure, dpi=300, bbox_inches="tight")
    plt.close()

    english_query_count = len(list((root / "en" / "queries").iterdir()))
    spanish_query_count = len(list((root / "es" / "queries").iterdir()))
    english_resume_count = len(list((root / "en" / "corpus").iterdir()))
    spanish_resume_count = len(list((root / "es" / "corpus").iterdir()))

    parallel_profiles = (
        english_query_count == spanish_query_count == 40
        and english_resume_count == spanish_resume_count == 476
        and email_multiset(root, "en") == email_multiset(root, "es")
    )

    jobs_table = pd.DataFrame(
        {
            "query_id": list(job_titles.keys()),
            "job_title": list(job_titles.values()),
            "domain": [DOMAIN_BY_TITLE[title] for title in job_titles.values()],
        }
    )

    jobs_table.to_csv(
        output_dir / "testing_job_domains.csv",
        index=False,
    )
    resumes.to_csv(
        output_dir / "testing_candidate_summary.csv",
        index=False,
    )

    print("\nGENERAL STRUCTURE")
    print(f"English job descriptions: {english_query_count}")
    print(f"Spanish job descriptions: {spanish_query_count}")
    print(f"English resumes: {english_resume_count}")
    print(f"Spanish resumes: {spanish_resume_count}")
    print(
        "Spanish collection is a translated parallel version:",
        parallel_profiles,
    )

    print("\nJOB DOMAINS")
    print(domain_counts.sort_values(ascending=False).to_string())

    print("\nBINARY NAME-BASED GENDER ESTIMATE")
    print(gender_counts.to_string())

    print("\nHIGHEST IDENTIFIED EDUCATION LEVEL")
    print(resumes["highest_education"].value_counts().to_string())

    print("\nNUMBER OF LISTED PROFESSIONAL POSITIONS")
    print(
        resumes["professional_positions"]
        .value_counts()
        .sort_index()
        .to_string()
    )
    print(f"Mean: {resumes['professional_positions'].mean():.2f}")
    print(f"Median: {resumes['professional_positions'].median():.0f}")

    print("\nFILES CREATED")
    print(domain_figure)
    print(gender_figure)
    print(output_dir / "testing_job_domains.csv")
    print(output_dir / "testing_candidate_summary.csv")


if __name__ == "__main__":
    main()

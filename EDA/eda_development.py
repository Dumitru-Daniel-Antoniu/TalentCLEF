"""
Exploratory Data Analysis — TalentCLEF Development Dataset
Structure: corpus/ (resumes)  |  queries/ (job descriptions)  |  qrels.tsv
==========================================================================
Produces:
  - Detailed console statistics for dissertation writing
  - Publication-quality figures saved to ./eda_dev_figures/
"""

import os
import re
import glob
import collections
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")
os.makedirs("eda_dev_figures", exist_ok=True)

DEV_BASE   = "/kaggle/input/datasets/danielantoniudumitru/clef-talentclef-subtaska/A/Development/en"
CORPUS_DIR = os.path.join(DEV_BASE, "corpus")
QUERY_DIR  = os.path.join(DEV_BASE, "queries")
QRELS_FILE = os.path.join(DEV_BASE, "qrels.tsv")

plt.rcParams.update({
    "font.family"      : "DejaVu Sans",
    "font.size"        : 11,
    "axes.spines.top"  : False,
    "axes.spines.right": False,
    "axes.titlesize"   : 13,
    "axes.titleweight" : "bold",
    "figure.dpi"       : 130,
    "savefig.dpi"      : 150,
    "savefig.bbox"     : "tight",
})
PALETTE = [
    "#2D6A9F","#E07B39","#3BAA6E","#C0392B",
    "#8E44AD","#16A085","#F39C12","#2C3E50",
    "#1ABC9C","#E74C3C","#95A5A6","#7F8C8D",
]

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except Exception:
        return ""

print("Loading corpus (resumes) …")
corpus = {}
for fp in sorted(glob.glob(os.path.join(CORPUS_DIR, "*"))):
    fid = os.path.basename(fp)
    corpus[fid] = read_file(fp)

print("Loading queries (job descriptions) …")
queries = {}
for fp in sorted(glob.glob(os.path.join(QUERY_DIR, "*"))):
    fid = os.path.basename(fp)
    queries[fid] = read_file(fp)

print("Loading qrels …")
qrels = pd.read_csv(QRELS_FILE, sep="\t", header=None,
                    names=["q_id", "iter", "c_id", "relevance"])
qrels["q_id"] = qrels["q_id"].astype(str)
qrels["c_id"] = qrels["c_id"].astype(str)

print(f"  Corpus files : {len(corpus):,}")
print(f"  Query files  : {len(queries):,}")
print(f"  Qrel pairs   : {len(qrels):,}")

def parse_resume(text):
    t = str(text)

    name_line = next((l.strip() for l in t.split("\n") if l.strip()), "")

    email_m = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", t)
    email   = email_m.group() if email_m else None

    location = None
    for line in t.split("\n")[:5]:
        lm = re.search(r"([A-Z][a-zA-Z\s,]+\d{4,})", line)
        if lm:
            location = lm.group(1).strip()
            break
    if not location:
        city_m = re.search(r"([A-Z][a-z]+(?: [A-Z][a-z]+)?),\s*\w+[-\d]*", t[:300])
        location = city_m.group() if city_m else None

    text_len = len(t)

    exp_section = ""
    em = re.search(r"PROFESSIONAL EXPERIENCE\s*\n(.*?)(?:EDUCATION|CERTIFICATIONS|SKILLS|\Z)",
                   t, re.DOTALL | re.IGNORECASE)
    if em:
        exp_section = em.group(1)

    job_titles = re.findall(
        r"\n([A-Z][A-Za-z &/,\-]+)\n[A-Za-z].+?,\s*\w+\n\w+",
        exp_section
    )
    job_titles = [j.strip() for j in job_titles if 3 < len(j.strip()) < 60]

    year_spans = re.findall(r"(January|February|March|April|May|June|July|August|"
                            r"September|October|November|December)\s+(\d{4})", exp_section)
    years = sorted(set(int(y[1]) for y in year_spans)) if year_spans else []
    career_start = min(years) if years else None
    career_yrs   = 2024 - career_start if career_start else None

    employers = re.findall(
        r"\n([A-Za-zÀ-ÿĀ-žА-яÑñ][A-Za-zÀ-ÿĀ-žА-яÑñ0-9 &,.\-']+),\s*\w+\n"
        r"\w+.+?\d{4}",
        exp_section
    )

    edu_section = ""
    edu_m = re.search(r"EDUCATION\s*\n(.*?)(?:CERTIFICATIONS|SKILLS|PROFESSIONAL AFFI|\Z)",
                      t, re.DOTALL | re.IGNORECASE)
    if edu_m:
        edu_section = edu_m.group(1)

    degrees = re.findall(
        r"(Master of [^\n]+|Bachelor of [^\n]+|Doctor of [^\n]+|"
        r"PhD[^\n]*|MBA[^\n]*|Juris Doctor[^\n]*|Associate[^\n]+)",
        edu_section, re.IGNORECASE
    )
    degrees = [d.strip() for d in degrees]

    grad_years = [int(y) for y in re.findall(r"Graduated:\s*\w+\s+(\d{4})", edu_section)]

    universities = re.findall(
        r"\n([A-Za-zÀ-ÿ\- ]+(?:University|Institute|College|Universit[eéä]|École|"
        r"Hochschule|Universidade|Universidad)[^\n]*)\n",
        edu_section, re.IGNORECASE
    )
    universities = [u.strip() for u in universities]

    cert_section = ""
    cert_m = re.search(r"CERTIFICATIONS\s*\n(.*?)(?:SKILLS|PROFESSIONAL|EDUCATION|\Z)",
                       t, re.DOTALL | re.IGNORECASE)
    if cert_m:
        cert_section = cert_m.group(1)
    cert_names = re.findall(r"\n([A-Z][^\n]{5,60})\n", cert_section)
    cert_names = [c.strip() for c in cert_names if not re.match(r"^\d{4}", c)]

    skills_raw = ""
    sk_m = re.search(r"SKILLS\s*\n(.*?)(?:PROFESSIONAL AFFI|LANGUAGES|\Z)",
                     t, re.DOTALL | re.IGNORECASE)
    if sk_m:
        skills_raw = sk_m.group(1)

    skill_tokens = []
    for line in skills_raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            line = line.split(":", 1)[1]
        parts = re.split(r"[,•\-/]+", line)
        for p in parts:
            p = p.strip()
            if 2 < len(p) < 50:
                skill_tokens.append(p)

    seniority = "Mid-level"
    title_str = " ".join(job_titles[:2]).lower() if job_titles else ""
    if any(k in title_str for k in ["senior", "principal", "director",
                                     "head", "lead", "chief", "vp", "manager"]):
        seniority = "Senior / Lead"
    elif any(k in title_str for k in ["junior", "intern", "assistant",
                                       "associate", "coordinator", "trainee"]):
        seniority = "Junior / Entry"

    return {
        "name"         : name_line,
        "email"        : email,
        "location"     : location,
        "text_len"     : text_len,
        "job_titles"   : job_titles,
        "career_start" : career_start,
        "career_yrs"   : career_yrs,
        "n_employers"  : len(set(employers)),
        "degrees"      : degrees,
        "grad_years"   : grad_years,
        "universities" : universities,
        "cert_names"   : cert_names,
        "skill_tokens" : skill_tokens,
        "seniority"    : seniority,
    }


def parse_jd(text):
    t = str(text)

    title = next((l.strip() for l in t.split("\n") if l.strip()), "")

    text_len = len(t)

    req_section = ""
    rm = re.search(r"Required Skills?\s*\n(.*?)(?:Responsibilities|What We Offer|How to Apply|\Z)",
                   t, re.DOTALL | re.IGNORECASE)
    if rm:
        req_section = rm.group(1)

    req_skills = [
        s.strip("- •").strip()
        for s in req_section.split("\n")
        if s.strip() and len(s.strip()) > 2
    ]
    req_skills = [s for s in req_skills if not re.match(r"^(Required|Skills?)", s, re.I)]

    resp_section = ""
    res_m = re.search(r"Responsibilities\s*\n(.*?)(?:What We Offer|How to Apply|Required|\Z)",
                      t, re.DOTALL | re.IGNORECASE)
    if res_m:
        resp_section = res_m.group(1)
    n_resp = len([r for r in resp_section.split("\n")
                  if r.strip().startswith("-") or r.strip().startswith("•")])

    t_lower = t.lower()
    seniority = "Mid-level"
    if any(k in t_lower for k in ["senior", "principal", "lead", "head of",
                                    "director", "manager", "chief"]):
        seniority = "Senior / Lead"
    elif any(k in t_lower for k in ["junior", "entry level", "graduate",
                                     "intern", "trainee", "associate"]):
        seniority = "Junior / Entry"

    has_about = bool(re.search(r"About the Role", t, re.I))

    return {
        "title"        : title,
        "text_len"     : text_len,
        "req_skills"   : req_skills,
        "n_resp"       : n_resp,
        "seniority"    : seniority,
        "has_about"    : has_about,
    }


print("Parsing corpus …")
corpus_parsed = {fid: parse_resume(txt) for fid, txt in corpus.items()}
print("Parsing queries …")
query_parsed  = {fid: parse_jd(txt) for fid, txt in queries.items()}

cp = pd.DataFrame.from_dict(corpus_parsed, orient="index")
qp = pd.DataFrame.from_dict(query_parsed,  orient="index")
cp.index.name = "c_id"
qp.index.name = "q_id"

positives = qrels[qrels["relevance"] == 1]
pos_per_query = positives.groupby("q_id")["c_id"].count().reset_index()
pos_per_query.columns = ["q_id", "n_positives"]

covered_corpus = positives["c_id"].nunique()

sep = "─" * 65

print(f"\n{sep}")
print("SECTION 1: DEVELOPMENT SET OVERVIEW")
print(sep)
print(f"  Corpus files (resumes)        : {len(corpus):,}")
print(f"  Query files (job descriptions): {len(queries):,}")
print(f"  Total qrel pairs              : {len(qrels):,}")
print(f"  Positive pairs (relevance=1)  : {(qrels['relevance']==1).sum():,}")
print(f"  Unique queries in qrels       : {qrels['q_id'].nunique():,}")
print(f"  Unique corpus docs in qrels   : {qrels['c_id'].nunique():,}")
print(f"  Corpus docs covered (matched) : {covered_corpus:,} / {len(corpus):,}")
print(f"  Coverage ratio                : {covered_corpus/len(corpus)*100:.1f}%")

print(f"\n{sep}")
print("SECTION 2: QRELS — RELEVANCE DISTRIBUTION")
print(sep)
print("\n  Positive pairs per query:")
for _, row in pos_per_query.sort_values("n_positives", ascending=False).iterrows():
    q_title = query_parsed.get(row["q_id"], {}).get("title", row["q_id"])
    print(f"    Q{row['q_id']:<8} {q_title[:45]:<45}: {row['n_positives']:>3} matches")
print(f"\n  Mean positives per query : {pos_per_query['n_positives'].mean():.1f}")
print(f"  Min positives per query  : {pos_per_query['n_positives'].min()}")
print(f"  Max positives per query  : {pos_per_query['n_positives'].max()}")

print(f"\n{sep}")
print("SECTION 3: JOB DESCRIPTIONS (QUERIES)")
print(sep)
print("\n  All query job titles:")
for qid, row in qp.iterrows():
    print(f"    [{qid}] {row['title']}")
print(f"\n  JD text length:")
print(f"    Min    : {qp['text_len'].min():,} chars")
print(f"    Max    : {qp['text_len'].max():,} chars")
print(f"    Mean   : {qp['text_len'].mean():,.0f} chars")
print(f"\n  Seniority level in JDs:")
for s, c in qp["seniority"].value_counts().items():
    print(f"    {s:<20}: {c}")
print(f"\n  Mean responsibilities per JD : {qp['n_resp'].mean():.1f}")
print(f"\n  All required skills (across all JDs):")
all_jd_skills = [s for row in qp["req_skills"] for s in row]
for sk, c in collections.Counter(all_jd_skills).most_common(30):
    print(f"    {sk:<40}: {c}")

print(f"\n{sep}")
print("SECTION 4: RESUMES (CORPUS)")
print(sep)
print(f"\n  Resume text length:")
print(f"    Min    : {cp['text_len'].min():,} chars")
print(f"    Max    : {cp['text_len'].max():,} chars")
print(f"    Mean   : {cp['text_len'].mean():,.0f} chars")
print(f"    Median : {cp['text_len'].median():,.0f} chars")
print(f"\n  Career span (years since first recorded role):")
cy = cp["career_yrs"].dropna()
print(f"    Min    : {cy.min():.0f} years")
print(f"    Max    : {cy.max():.0f} years")
print(f"    Mean   : {cy.mean():.1f} years")
print(f"\n  Seniority distribution:")
for s, c in cp["seniority"].value_counts().items():
    print(f"    {s:<20}: {c:>4}  ({c/len(cp)*100:.1f}%)")
print(f"\n  Number of distinct employers per resume:")
ne = cp["n_employers"]
print(f"    Min : {ne.min()}   Max : {ne.max()}   Mean : {ne.mean():.1f}")
print(f"\n  Degree types found:")
all_degrees = [d for row in cp["degrees"] for d in row]
for d, c in collections.Counter(all_degrees).most_common(20):
    print(f"    {d[:55]:<55}: {c}")
print(f"\n  Universities (top 25):")
all_univs = [u for row in cp["universities"] for u in row]
for u, c in collections.Counter(all_univs).most_common(25):
    print(f"    {u[:55]:<55}: {c}")
print(f"\n  Certifications (top 20):")
all_certs = [c for row in cp["cert_names"] for c in row]
for ce, c in collections.Counter(all_certs).most_common(20):
    print(f"    {ce[:55]:<55}: {c}")
print(f"\n  Top 30 skills across resumes:")
all_resume_skills = [s for row in cp["skill_tokens"] for s in row]
for sk, c in collections.Counter(all_resume_skills).most_common(30):
    print(f"    {sk:<40}: {c}")

print(f"\n{sep}")
print("SECTION 5: SKILL OVERLAP — MATCHED vs NON-MATCHED PAIRS")
print(sep)
def jaccard(set_a, set_b):
    a, b = set(s.lower() for s in set_a), set(s.lower() for s in set_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

pos_jaccard, neg_jaccard = [], []
pos_set = set(zip(positives["q_id"], positives["c_id"]))

for _, row in qrels.iterrows():
    q, c = str(row["q_id"]), str(row["c_id"])
    q_skills = query_parsed.get(q, {}).get("req_skills", [])
    c_skills = corpus_parsed.get(c, {}).get("skill_tokens", [])
    j = jaccard(q_skills, c_skills)
    if row["relevance"] == 1:
        pos_jaccard.append(j)
    else:
        neg_jaccard.append(j)

print(f"\n  Skill Jaccard similarity — POSITIVE pairs : "
      f"mean={np.mean(pos_jaccard):.3f}  median={np.median(pos_jaccard):.3f}")
print(f"  Skill Jaccard similarity — NEGATIVE pairs : "
      f"mean={np.mean(neg_jaccard):.3f}  median={np.median(neg_jaccard):.3f}")


fig, axes = plt.subplots(1, 2, figsize=(15, 5))
fig.suptitle("Figure 1 — Qrels Structure and Positive Pair Distribution",
             fontsize=14, fontweight="bold")

ppq = pos_per_query.sort_values("n_positives", ascending=False)
q_labels = [
    f"Q{r['q_id']}\n{query_parsed.get(r['q_id'],{}).get('title','')[:18]}"
    for _, r in ppq.iterrows()
]
bars = axes[0].bar(q_labels, ppq["n_positives"],
                   color=PALETTE[:len(ppq)], edgecolor="white", width=0.65)
axes[0].bar_label(bars, fontsize=8.5, padding=2)
axes[0].set_title(f"Positive Matches per Query\n(Total: {len(positives):,})")
axes[0].set_ylabel("Number of Matched Resumes")
axes[0].tick_params(axis="x", rotation=30, labelsize=7)
axes[0].set_ylim(0, ppq["n_positives"].max() * 1.2)

axes[1].hist(ppq["n_positives"], bins=min(15, len(ppq)),
             color="#2D6A9F", edgecolor="white", alpha=0.9)
axes[1].axvline(ppq["n_positives"].mean(), color="#C0392B", linestyle="--", linewidth=1.8,
                label=f"Mean: {ppq['n_positives'].mean():.1f}")
axes[1].set_title("Distribution of Positive Count per Query")
axes[1].set_xlabel("Number of Positive Resumes")
axes[1].set_ylabel("Frequency")
axes[1].legend()

plt.tight_layout()
plt.savefig("eda_dev_figures/fig1_qrels_structure.png")
plt.close()
print("\nSaved: eda_dev_figures/fig1_qrels_structure.png")

fig = plt.figure(figsize=(16, 9))
fig.suptitle("Figure 2 — Job Description Analysis (Development Queries)",
             fontsize=14, fontweight="bold")
gs = GridSpec(2, 2, figure=fig, hspace=0.5, wspace=0.4)

ax = fig.add_subplot(gs[0, 0])
ax.bar(range(len(qp)), sorted(qp["text_len"]),
       color="#2D6A9F", edgecolor="white", width=0.7)
ax.axhline(qp["text_len"].mean(), color="#C0392B", linestyle="--", linewidth=1.5,
           label=f"Mean: {qp['text_len'].mean():,.0f}")
ax.set_title("JD Text Length (characters)")
ax.set_xlabel("Job Description (sorted)")
ax.set_ylabel("Characters")
ax.legend(fontsize=9)

ax2 = fig.add_subplot(gs[0, 1])
n_skills = [len(row) for row in qp["req_skills"]]
ax2.bar(range(len(n_skills)), sorted(n_skills),
        color="#3BAA6E", edgecolor="white", width=0.7)
ax2.axhline(np.mean(n_skills), color="#C0392B", linestyle="--", linewidth=1.5,
            label=f"Mean: {np.mean(n_skills):.1f}")
ax2.set_title("Required Skills per Job Description")
ax2.set_xlabel("Job Description (sorted)")
ax2.set_ylabel("Number of Skills")
ax2.legend(fontsize=9)

ax3 = fig.add_subplot(gs[1, :])
top_jd_skills = collections.Counter(all_jd_skills).most_common(20)
sk_names = [s[0][:35] for s in reversed(top_jd_skills)]
sk_vals  = [s[1] for s in reversed(top_jd_skills)]
bars3 = ax3.barh(sk_names, sk_vals, color="#E07B39", edgecolor="white", height=0.7)
for i, v in enumerate(sk_vals):
    ax3.text(v + 0.05, i, str(v), va="center", fontsize=8)
ax3.set_title("Top 20 Required Skills Across All Job Descriptions")
ax3.set_xlabel("Occurrences")

plt.savefig("eda_dev_figures/fig2_jd_analysis.png")
plt.close()
print("Saved: eda_dev_figures/fig2_jd_analysis.png")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Figure 3 — Resume Length and Career Span",
             fontsize=14, fontweight="bold")

axes[0].hist(cp["text_len"], bins=40, color="#2D6A9F", edgecolor="white", alpha=0.9)
axes[0].axvline(cp["text_len"].mean(), color="#C0392B", linestyle="--", linewidth=1.8,
                label=f"Mean: {cp['text_len'].mean():,.0f} chars")
axes[0].axvline(cp["text_len"].median(), color="#E07B39", linestyle=":", linewidth=1.8,
                label=f"Median: {cp['text_len'].median():,.0f} chars")
axes[0].set_title("Resume Text Length Distribution")
axes[0].set_xlabel("Characters")
axes[0].set_ylabel("Count")
axes[0].legend()

cy_vals = cp["career_yrs"].dropna()
axes[1].hist(cy_vals, bins=25, color="#3BAA6E", edgecolor="white", alpha=0.9)
axes[1].axvline(cy_vals.mean(), color="#C0392B", linestyle="--", linewidth=1.8,
                label=f"Mean: {cy_vals.mean():.1f} yrs")
axes[1].set_title("Career Span\n(years since first recorded role, as of 2024)")
axes[1].set_xlabel("Years")
axes[1].set_ylabel("Count")
axes[1].legend()

plt.tight_layout()
plt.savefig("eda_dev_figures/fig3_resume_length_career.png")
plt.close()
print("Saved: eda_dev_figures/fig3_resume_length_career.png")

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle("Figure 4 — Education Level and Certifications",
             fontsize=14, fontweight="bold")

deg_labels  = []
deg_cats    = collections.Counter()
for d in all_degrees:
    dl = d.lower()
    if "master" in dl or "mba" in dl:
        deg_cats["Master"] += 1
    elif "bachelor" in dl or "b.sc" in dl or "b.s." in dl:
        deg_cats["Bachelor"] += 1
    elif "doctor" in dl or "phd" in dl:
        deg_cats["Doctor / PhD"] += 1
    elif "juris" in dl or "llm" in dl or "llb" in dl:
        deg_cats["Law Degree"] += 1
    else:
        deg_cats["Other"] += 1

if deg_cats:
    labels_d = list(deg_cats.keys())
    vals_d   = list(deg_cats.values())
    axes[0].pie(vals_d, labels=labels_d, autopct="%1.1f%%",
                colors=PALETTE[:len(labels_d)], startangle=140,
                textprops={"fontsize": 10})
    axes[0].set_title("Degree Types in Corpus")
else:
    axes[0].text(0.5, 0.5, "No degree data parsed", ha="center", va="center")
    axes[0].set_title("Degree Types in Corpus")

top_certs = collections.Counter(all_certs).most_common(15)
if top_certs:
    ce_names = [c[0][:42] for c in reversed(top_certs)]
    ce_vals  = [c[1] for c in reversed(top_certs)]
    axes[1].barh(ce_names, ce_vals, color="#8E44AD", edgecolor="white", height=0.7)
    axes[1].set_title("Top 15 Certifications in Corpus")
    axes[1].set_xlabel("Occurrences")
    axes[1].tick_params(axis="y", labelsize=8)
    for i, v in enumerate(ce_vals):
        axes[1].text(v + 0.05, i, str(v), va="center", fontsize=8)

plt.tight_layout()
plt.savefig("eda_dev_figures/fig4_education_certs.png")
plt.close()
print("Saved: eda_dev_figures/fig4_education_certs.png")

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("Figure 5 — Seniority Level Distribution",
             fontsize=14, fontweight="bold")

sen_cp = cp["seniority"].value_counts()
bars_s = axes[0].bar(sen_cp.index, sen_cp.values,
                     color=PALETTE[:3], edgecolor="white", width=0.55)
axes[0].bar_label(bars_s, labels=[f"{v}\n({v/len(cp)*100:.1f}%)"
                                   for v in sen_cp.values],
                  fontsize=9.5, padding=4)
axes[0].set_title("Corpus — Resume Seniority")
axes[0].set_ylabel("Count")
axes[0].set_ylim(0, sen_cp.max() * 1.25)

sen_qp = qp["seniority"].value_counts()
bars_q = axes[1].bar(sen_qp.index, sen_qp.values,
                     color=PALETTE[:3], edgecolor="white", width=0.55)
axes[1].bar_label(bars_q, labels=[f"{v}\n({v/len(qp)*100:.1f}%)"
                                   for v in sen_qp.values],
                  fontsize=9.5, padding=4)
axes[1].set_title("Queries — JD Seniority Level")
axes[1].set_ylabel("Count")
axes[1].set_ylim(0, sen_qp.max() * 1.25)

plt.tight_layout()
plt.savefig("eda_dev_figures/fig5_seniority.png")
plt.close()
print("Saved: eda_dev_figures/fig5_seniority.png")

fig, ax = plt.subplots(figsize=(10, 5))
fig.suptitle("Figure 6 — Skill Overlap: Matched vs Non-Matched Pairs",
             fontsize=14, fontweight="bold")

bins = np.linspace(0, max(max(pos_jaccard, default=0),
                          max(neg_jaccard, default=0)) + 0.05, 30)
if pos_jaccard:
    ax.hist(pos_jaccard, bins=bins, alpha=0.7, color="#2D6A9F",
            label=f"Positive pairs (n={len(pos_jaccard)}, "
                  f"mean={np.mean(pos_jaccard):.3f})", density=True)
if neg_jaccard:
    ax.hist(neg_jaccard, bins=bins, alpha=0.7, color="#C0392B",
            label=f"Negative pairs (n={len(neg_jaccard)}, "
                  f"mean={np.mean(neg_jaccard):.3f})", density=True)
ax.set_xlabel("Jaccard Similarity (Required Skills ∩ Resume Skills)")
ax.set_ylabel("Density")
ax.set_title("Skill Overlap Distribution by Relevance Label\n"
             "(Higher overlap expected for relevant pairs)")
ax.legend(fontsize=10)

plt.tight_layout()
plt.savefig("eda_dev_figures/fig6_skill_overlap.png")
plt.close()
print("Saved: eda_dev_figures/fig6_skill_overlap.png")

fig, axes = plt.subplots(1, 2, figsize=(17, 8))
fig.suptitle("Figure 7 — Top Skills in Corpus and Queries",
             fontsize=14, fontweight="bold")

top_resume_skills = collections.Counter(all_resume_skills).most_common(25)
rs_names = [s[0][:38] for s in reversed(top_resume_skills)]
rs_vals  = [s[1] for s in reversed(top_resume_skills)]
axes[0].barh(rs_names, rs_vals, color="#2D6A9F", edgecolor="white", height=0.72)
axes[0].set_title("Top 25 Skills — Corpus (Resumes)")
axes[0].set_xlabel("Occurrences")
axes[0].tick_params(axis="y", labelsize=8)

top_jd_sk = collections.Counter(all_jd_skills).most_common(25)
js_names  = [s[0][:38] for s in reversed(top_jd_sk)]
js_vals   = [s[1] for s in reversed(top_jd_sk)]
axes[1].barh(js_names, js_vals, color="#3BAA6E", edgecolor="white", height=0.72)
axes[1].set_title("Top 25 Skills — Queries (Job Descriptions)")
axes[1].set_xlabel("Occurrences")
axes[1].tick_params(axis="y", labelsize=8)

plt.tight_layout()
plt.savefig("eda_dev_figures/fig7_skills_corpus_queries.png")
plt.close()
print("Saved: eda_dev_figures/fig7_skills_corpus_queries.png")

fig = plt.figure(figsize=(12, 7))
fig.suptitle("Figure 8 — Development Dataset: Key Statistics at a Glance",
             fontsize=14, fontweight="bold")
ax = fig.add_subplot(111)
ax.axis("off")

stats = [
    ["Corpus files (resumes)",         f"{len(corpus):,}"],
    ["Query files (job descriptions)", f"{len(queries):,}"],
    ["Total qrel pairs",               f"{len(qrels):,}"],
    ["Positive pairs (relevance = 1)", f"{(qrels['relevance']==1).sum():,}"],
    ["Unique queries in qrels",        f"{qrels['q_id'].nunique():,}"],
    ["Mean positives per query",       f"{pos_per_query['n_positives'].mean():.1f}"],
    ["Min / Max positives per query",  f"{pos_per_query['n_positives'].min()} / {pos_per_query['n_positives'].max()}"],
    ["Avg resume length",              f"{cp['text_len'].mean():,.0f} characters"],
    ["Avg JD length",                  f"{qp['text_len'].mean():,.0f} characters"],
    ["Mean career span",               f"{cy_vals.mean():.1f} years since first role"],
    ["Dominant seniority (corpus)",    cp["seniority"].value_counts().idxmax()],
    ["Skill overlap — positive pairs", f"Jaccard mean: {np.mean(pos_jaccard):.3f}"],
    ["Skill overlap — negative pairs", f"Jaccard mean: {np.mean(neg_jaccard):.3f}"],
    ["Missing values",                 "None (all files present)"],
]

table = ax.table(
    cellText=stats,
    colLabels=["Statistic", "Value"],
    cellLoc="left",
    loc="center",
    bbox=[0, 0, 1, 1],
)
table.auto_set_font_size(False)
table.set_fontsize(10)
for (row, col), cell in table.get_celld().items():
    cell.set_edgecolor("lightgrey")
    if row == 0:
        cell.set_facecolor("#2D6A9F")
        cell.set_text_props(color="white", fontweight="bold")
    elif row % 2 == 0:
        cell.set_facecolor("#EEF4FA")
    else:
        cell.set_facecolor("white")
    cell.set_height(0.065)

plt.savefig("eda_dev_figures/fig8_summary_card.png")
plt.close()
print("Saved: eda_dev_figures/fig8_summary_card.png")

print(f"\n{'─'*65}")
print("All 8 figures saved to ./eda_dev_figures/")
print("Development set EDA complete.")

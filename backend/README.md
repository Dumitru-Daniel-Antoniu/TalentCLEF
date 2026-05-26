# Backend — FastAPI Resume Ranking Service

This backend exposes APIs used by the React frontend to upload resumes, accept a job description, compute semantic embeddings, and rank uploaded candidates.

Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate    # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

2. Run the server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Notes
- The ML model (sentence-transformers/all-MiniLM-L6-v2) is downloaded on first run.
- Uploaded files are stored in `uploads/` and parsed into text.
- This service focuses on concise, modular ML logic and simple in-memory storage for demo purposes.

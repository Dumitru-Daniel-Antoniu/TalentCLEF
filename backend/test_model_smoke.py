"""Simple smoke test that imports the backend embeddings loader
and computes a single embedding to verify model availability.
"""
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import os
    import sys
    import numpy as np

    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    from app.ml import embeddings
except Exception as e:
    logger.exception("Import failed: %s", e)
    raise


def main():
    try:
        logger.info("Running smoke test for embeddings")
        sample_text = (
            "Software engineer with Python, machine learning, and data science experience."
        )
        emb = embeddings.get_embedding(sample_text)
        if emb is None:
            print("EMB_FAIL: embedding is None")
            sys.exit(2)
        print("EMB_OK: length=", len(emb))
        print("First values:", emb[:8].tolist() if hasattr(emb, "tolist") else list(emb)[:8])
    except Exception as e:
        import traceback

        traceback.print_exc()
        print("SMOKE_TEST_ERROR:", e)
        sys.exit(3)


if __name__ == '__main__':
    main()

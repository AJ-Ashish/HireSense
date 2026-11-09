"""
calibrate.py - see the raw similarity numbers your AI backend produces.

Usage (from the backend folder):
    python calibrate.py sample_job.txt path/to/folder_with_resumes

It prints one raw similarity per resume (0 to 1) and suggests SIM_LOW and
SIM_HIGH values. Put them in your .env (and in Render's Environment tab) so the
match percentages spread nicely from weak to strong resumes.
"""
import os
import sys
import glob

from dotenv import load_dotenv
load_dotenv()

import ranker
from parser import extract_text, clean_text

if len(sys.argv) != 3:
    sys.exit(__doc__)

job_text = open(sys.argv[1], encoding="utf-8").read()
files = sorted(f for f in glob.glob(os.path.join(sys.argv[2], "*"))
               if f.lower().endswith((".pdf", ".docx", ".txt")))

rows = []
for f in files:
    try:
        text = clean_text(extract_text(f))
        if not text:
            continue
        sim = float(ranker._embed_one(job_text) @ ranker._embed_one(text))
        rows.append((sim, os.path.basename(f)))
    except Exception as e:
        print("skipped", os.path.basename(f), "-", e)

if not rows:
    sys.exit("No readable resumes found.")

print(f"Backend: {ranker.embedding_backend()}\n")
for sim, name in sorted(rows, reverse=True):
    print(f"{sim:6.3f}  {name}")

lo, hi = min(r[0] for r in rows), max(r[0] for r in rows)
print(f"\nLowest {lo:.3f}, highest {hi:.3f}")
print(f"Suggested:  SIM_LOW={max(0.0, lo - 0.05):.2f}   SIM_HIGH={min(1.0, hi + 0.03):.2f}")

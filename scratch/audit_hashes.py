import hashlib
import os
import subprocess

src_dir = r"C:\Users\lenovo\Desktop\ResumeAnalyzerAgent\ResumeAnalyzerAgent\backend\app"
dst_dir = r"C:\Users\lenovo\Desktop\Adaptive-Interview-Intelligence\backend\resume_analyzer\app"

files = [
    "__init__.py",
    os.path.join("agents", "resume_parser.py"),
    os.path.join("agents", "job_description_analyzer.py"),
    os.path.join("agents", "skills_matcher.py"),
    os.path.join("agents", "ats_scorer.py"),
    os.path.join("agents", "integrity_detector.py"),
    os.path.join("agents", "resume_improver.py"),
    os.path.join("agents", "orchestrator.py"),
    os.path.join("schemas", "__init__.py"),
    os.path.join("schemas", "resume.py"),
    os.path.join("schemas", "job_description.py"),
    os.path.join("schemas", "analysis.py"),
    os.path.join("schemas", "integrity.py"),
    os.path.join("services", "extractor.py"),
    os.path.join("services", "gemini_service.py"),
    os.path.join("database", "db.py"),
]

print("=== SHA-256 AUDIT OF COPIED SOURCE FILES ===")
all_match = True
for f in files:
    src_path = os.path.join(src_dir, f)
    dst_path = os.path.join(dst_dir, f)
    with open(src_path, "rb") as s_fp:
        src_hash = hashlib.sha256(s_fp.read()).hexdigest().upper()
    with open(dst_path, "rb") as d_fp:
        dst_hash = hashlib.sha256(d_fp.read()).hexdigest().upper()
    match = (src_hash == dst_hash)
    if not match:
        all_match = False
    print(f"{f.replace(os.sep, '/')} | Match: {match}")
    print(f"  SRC: {src_hash}")
    print(f"  DST: {dst_hash}")

print(f"\nAll 16 copied files byte-for-byte identical: {all_match}")

print("\n=== GIT STATUS OF ORIGINAL SOURCE PROJECT ===")
git_status = subprocess.run(
    ["git", "status", "--porcelain"],
    cwd=r"C:\Users\lenovo\Desktop\ResumeAnalyzerAgent\ResumeAnalyzerAgent",
    capture_output=True,
    text=True,
)
print(f"Original repo porcelain git status output:\n'{git_status.stdout.strip()}'")
if not git_status.stdout.strip():
    print("Original ResumeAnalyzerAgent repository is completely clean and untouched.")
else:
    print("WARNING: Uncommitted changes in original repo.")

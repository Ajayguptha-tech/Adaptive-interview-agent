import os
import hashlib

src_root = r"C:\Users\lenovo\Desktop\ResumeAnalyzerAgent\ResumeAnalyzerAgent"
dest_root = r"C:\Users\lenovo\Desktop\Adaptive-Interview-Intelligence\backend\resume_analyzer"

files = [
    r"app\core\config.py",
    r"app\core\logging.py",
    r"app\models\resume.py",
    r"app\models\job_description.py",
    r"app\models\audit.py",
    r"app\models\skills.py",
    r"app\models\scoring.py",
    r"app\models\improvement.py",
    r"app\services\document_extractor.py",
    r"app\services\gemini_service.py",
    r"app\agents\resume_parser.py",
    r"app\agents\integrity_detector.py",
    r"app\agents\jd_analyzer.py",
    r"app\agents\skills_matcher.py",
    r"app\agents\ats_scorer.py",
    r"app\agents\improver.py",
]

all_match = True
for rel in files:
    src_path = os.path.join(src_root, rel)
    dest_path = os.path.join(dest_root, rel)
    h_src = hashlib.sha256(open(src_path, "rb").read()).hexdigest()
    h_dest = hashlib.sha256(open(dest_path, "rb").read()).hexdigest()
    match = (h_src == h_dest)
    print(f"{rel}: {'MATCH' if match else 'MISMATCH'} ({h_src[:12]}...)")
    if not match:
        all_match = False

print(f"\nTotal files: {len(files)} | All 100% Byte-for-Byte Identical: {all_match}")

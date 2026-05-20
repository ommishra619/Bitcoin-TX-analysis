import sys
try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf not installed.")
    sys.exit(1)

import os

pdf_path = "2509.03260v1.pdf"
out_path = "2509.03260v1_extracted.txt"

if not os.path.exists(pdf_path):
    print(f"File {pdf_path} not found.")
    sys.exit(1)

reader = PdfReader(pdf_path)
text = ""
for page in reader.pages:
    text += page.extract_text() + "\n\n"

with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Successfully extracted {len(reader.pages)} pages to {out_path}.")

import json
import os
import sys
import argparse
from typing import List

try:
    import PyPDF2  # for PDF
except ImportError:
    PyPDF2 = None

def chunk_text(text: str, chunk_size: int = 650, overlap: int = 130) -> List[str]:
    """
    Simple word-aware chunker with overlap.
    Tries to avoid splitting in the middle of sentences too badly.
    """
    if not text.strip():
        return []
    
    words = text.split()
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from PDF (joins pages with double newlines)"""
    if PyPDF2 is None:
        raise ImportError("PyPDF2 is not installed. Install it with: pip install PyPDF2")
    
    full_text = []
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text.append(text.strip())
    return "\n\n".join(full_text)


def extract_text_from_plain(file_path: str) -> str:
    """Read text from .txt or .md files"""
    encodings = ['utf-8', 'latin-1', 'iso-8859-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode file {file_path} with common encodings")


def file_to_json(
    input_file: str,
    output_file: str = None,
    chunk_size: int = 650,
    overlap: int = 130
):
    """
    Universal converter:
    - Takes any supported file
    - Chunks content
    - Saves as single JSON array
    """
    if not os.path.isfile(input_file):
        print(f"Error: File not found → {input_file}")
        return

    ext = os.path.splitext(input_file)[1].lower()

    print(f"Processing: {input_file} ({ext})")

    # ── Extract full text ───────────────────────────────────────
    try:
        if ext == '.pdf':
            full_text = extract_text_from_pdf(input_file)
        elif ext in ('.txt', '.md'):
            full_text = extract_text_from_plain(input_file)
        else:
            print(f"Unsupported file type: {ext}")
            print("Currently supported: .pdf, .txt, .md")
            return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    if not full_text.strip():
        print("No text content found in the file.")
        return

    # ── Chunking ─────────────────────────────────────────────────
    chunks = chunk_text(full_text, chunk_size=chunk_size, overlap=overlap)

    # ── Build structured documents ──────────────────────────────
    documents = []
    source_name = os.path.basename(input_file)

    for i, chunk_text in enumerate(chunks, 1):
        doc = {
            "id": f"chunk_{source_name}_{i:04d}",
            "text_content": chunk_text,
            "metadata": {
                "source": source_name,
                "file_type": ext,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_size_words_approx": len(chunk_text.split())
            }
        }
        documents.append(doc)

    # ── Decide output filename ──────────────────────────────────
    if output_file is None:
        base = os.path.splitext(input_file)[0]
        output_file = f"{base}_chunks.json"

    # ── Save as single JSON array ───────────────────────────────
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        print(f"\nSuccess!")
        print(f"→ Created {len(documents)} chunks")
        print(f"→ Saved to: {output_file}")
    except Exception as e:
        print(f"Error writing JSON: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Universal file → JSON chunk converter (PDF, TXT, MD)"
    )
    parser.add_argument("file", help="Path to the input file")
    parser.add_argument(
        "-o", "--output",
        help="Output JSON filename (default: <input>_chunks.json)"
    )
    parser.add_argument(
        "--chunk-size", type=int, default=650,
        help="Approximate words per chunk (default: 650)"
    )
    parser.add_argument(
        "--overlap", type=int, default=130,
        help="Words of overlap between chunks (default: 130)"
    )

    args = parser.parse_args()

    file_to_json(
        input_file=args.file,
        output_file=args.output,
        chunk_size=args.chunk_size,
        overlap=args.overlap
    )


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage examples:")
        print("  python ingest.py document.pdf")
        print("  python ingest.py notes.txt --output my_chunks.json")
        print("  python ingest.py history.md --chunk-size 500 --overlap 100\n")
        sys.exit(1)
    
    main()
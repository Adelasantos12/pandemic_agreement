import pdfplumber
import re

def parse_pdf_to_text(pdf_path: str) -> list[str]:
    """
    Extracts text from PDF, returning a list of text blocks (e.g. per page or per paragraph).
    """
    blocks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # Normalize whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                # Split by double newline to get paragraphs roughly, or just return page text
                # Returning page text is safer for LLM context window chunks
                blocks.append(text)
    return blocks

def parse_draft_to_clauses(pdf_path: str) -> list[dict]:
    """
    Parses a draft PDF into clauses.
    Returns list of dict: {article, paragraph, clause_key, text}
    """
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += "\n" + t

    # Heuristic parsing
    # Look for "Article X"
    # Then paragraphs inside.

    clauses = []

    # Split by Article
    # Regex for "Article <Number>" at start of line (or after newline)
    article_pattern = re.compile(r'(?:^|\n)(Article\s+\d+)', re.IGNORECASE)
    parts = article_pattern.split(text)

    current_article = None

    # parts[0] is pre-amble.
    # parts[1] is "Article 1", parts[2] is body.
    # parts[3] is "Article 2", parts[4] is body.

    for i in range(1, len(parts), 2):
        article_header = parts[i].strip()
        article_body = parts[i+1]

        # Parse paragraphs within article
        # Often numbered 1. Text... 2. Text...
        # Or just text blocks.

        # Simple splitting by newline for now, assuming paragraphs are separated by newlines
        paragraphs = [p.strip() for p in article_body.split('\n') if p.strip()]

        for idx, p_text in enumerate(paragraphs):
            # Try to detect paragraph number "1. "
            match = re.match(r'^(\d+)\.\s+(.*)', p_text)
            para_num = None
            if match:
                para_num = match.group(1)
                content = match.group(2)
            else:
                para_num = str(idx + 1) # Fallback numbering
                content = p_text

            # Clause key: Article_Para
            clause_key = f"{article_header}_{para_num}"

            clauses.append({
                "article": article_header,
                "paragraph": para_num,
                "clause_key": clause_key,
                "text": content
            })

    if not clauses:
        # Fallback if no Articles found: treat entire doc as one or split by pages
        # Just return chunks
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        for i, p in enumerate(paragraphs):
             clauses.append({
                "article": "General",
                "paragraph": str(i+1),
                "clause_key": f"Gen_{i+1}",
                "text": p
            })

    return clauses

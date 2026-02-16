import os
import json
from openai import OpenAI

def get_llm_client():
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY is required for LLM operations.")
    return OpenAI(api_key=api_key)

def extract_proposals(text: str, country_hint: str | None, source_type: str, topic_hint: str | None) -> list[dict]:
    client = get_llm_client()

    prompt = f"""
SYSTEM:
Eres un analista de negociaciones de tratados. Extraes propuestas y posiciones de países de manera conservadora.
Devuelves SOLO JSON válido que cumpla el esquema. No inventes país ni artículo si no están en el texto.

USER:
Texto:
<<<{text}>>>

Contexto (si existe):
- País esperado (si viene de PDF etiquetado): {country_hint}
- Tipo de fuente: {source_type}  (transcript|proposal_pdf|drafting_suggestions)
- Tema esperado (si existe): {topic_hint}

Tarea:
Extrae propuestas atómicas. Una propuesta atómica debe poder evaluarse contra el draft.
Incluye "country" solo si es explícito o hay COUNTRY_HINT por metadata del PDF.
Si el texto solo expresa apoyo/objeción sin redacción concreta, usa action SUPPORT/OPPOSE y proposed_text = null.
Si no hay propuestas, devuelve [].

Devuelve JSON con esta forma exacta:
[
  {{
    "country": "string|null",
    "action": "ADD|DELETE|MODIFY|SUPPORT|OPPOSE",
    "topic": "string",
    "target_ref": "string|null",
    "proposed_text": "string|null",
    "rationale": "string|null",
    "evidence_quote": "string",
    "confidence": 0.0
  }}
]
Reglas:
- confidence: 0.2 si es ambiguo; 0.6 si es claro; 0.85+ si hay redacción y referencia.
- evidence_quote: cita corta (máx 25 palabras) tomada del texto.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Recommended model for json extraction
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        content = response.choices[0].message.content
        if not content:
            return []

        # Parse JSON
        parsed = json.loads(content)
        # Handle if LLM wraps in { "proposals": [...] } or just list
        if isinstance(parsed, dict) and "proposals" in parsed:
            return parsed["proposals"]
        if isinstance(parsed, list):
            return parsed
        # Try to find list inside dict
        for k, v in parsed.items():
            if isinstance(v, list):
                return v
        return []
    except Exception as e:
        print(f"Error extracting proposals: {e}")
        return []

def verify_match(proposal, candidates):
    """
    Verifies if a proposal matches any candidate clause.
    candidates: list of dicts with {id, article, paragraph, text}
    """
    client = get_llm_client()

    # Prepare candidates JSON string
    candidates_json = json.dumps([
        {"id": c["db_id"], "article": c["article"], "paragraph": c["paragraph"], "text": c["text"]}
        for c in candidates
    ], ensure_ascii=False)

    prompt = f"""
SYSTEM:
Evalúas si una propuesta está implementada en un draft. Sé estricto y cita evidencia.

USER:
Propuesta:
- country: {proposal.country}
- action: {proposal.action}
- topic: {proposal.topic}
- target_ref: {proposal.target_ref}
- proposed_text: {proposal.proposed_text}
- rationale: {proposal.rationale}

Candidatos del draft (cada uno con id, article, paragraph, text):
{candidates_json}

Devuelve SOLO JSON:
{{
  "status": "adopted|partial|not_adopted|unclear",
  "best_clause_id": "string|null",
  "supporting_clause_ids": ["string"],
  "score": 0.0,
  "explanation": "string"
}}

Reglas:
- adopted: mismo significado y redacción muy cercana o inequívoca.
- partial: misma idea general pero falta parte importante o cambia condiciones.
- not_adopted: no aparece la idea.
- unclear: candidatos insuficientes o el texto es demasiado ambiguo.
- score: 0.9+ adopted claro; 0.6–0.8 partial; <0.5 not/unclear.
- best_clause_id debe ser el ID del candidato si aplica, o null.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)

        # Map best_clause_id back to integer DB ID if possible (the prompt asks for ID from candidates)
        best_id = parsed.get("best_clause_id")

        # Ensure correct type for DB ID (int)
        # The prompt might return string if ID was string in JSON. Candidates have integer IDs usually.
        # But wait, verify_match prompt receives candidates with 'db_id'.

        return {
            "status": parsed.get("status", "unclear"),
            "best_clause_db_id": int(best_id) if best_id and str(best_id).isdigit() else None,
            "supporting_clause_ids": parsed.get("supporting_clause_ids", []),
            "score": float(parsed.get("score", 0.0)),
            "explanation": parsed.get("explanation", "")
        }
    except Exception as e:
        print(f"Error verifying match: {e}")
        return {
            "status": "unclear",
            "best_clause_db_id": None,
            "supporting_clause_ids": [],
            "score": 0.0,
            "explanation": f"Error: {str(e)}"
        }

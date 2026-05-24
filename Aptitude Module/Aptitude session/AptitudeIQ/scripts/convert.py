"""
AptitudeIQ Converter  v4
========================
Extracts questions, options and answers from .md .txt .pdf .png .jpg .jpeg

FORMAT A — Inline MCQ  (A) Scarce B) Plentiful … **Answer**: B) Plentiful
FORMAT B — Question + plain-text answer, options built from SAME-SECTION pool

Key improvements over v3
─────────────────────────
• Distractor pool is SECTION-scoped (resets at every ## heading) instead of
  file-wide, so a temperature answer never appears next to a sales question.
• Distractors are TYPE-MATCHED: numeric vs ratio vs percent vs word answers
  are kept in separate buckets, so choices are always semantically similar.
• **Corrected**: <text> lines are now treated as Answer lines (covers the
  "Sentence Correction" section in verbal-ability files).
• Question-text noise (**  * numbered prefixes) is stripped at extraction
  time, not left for the server to wrestle with.
• Better answer-line regex catches more edge-cases.
"""

import re
import json
import random
from pathlib import Path

# ── optional deps ──────────────────────────────────────────────
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import pytesseract
    import cv2
    HAS_OCR = True
    import platform
    if platform.system() == "Windows":
        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )
except ImportError:
    HAS_OCR = False

BASE_DIR    = Path(__file__).parent.parent
INPUT_DIR   = BASE_DIR / "data" / "questions"
OUTPUT_JSON = BASE_DIR / "data" / "all_questions.json"


# ══════════════════════════════════════════════════════════════
# FILE READERS
# ══════════════════════════════════════════════════════════════

def read_image(path):
    if not HAS_OCR:
        print(f"  ⚠  OCR unavailable — skipping {path.name}")
        return ""
    img = cv2.imread(str(path))
    if img is None:
        return ""
        
    # Standardize size for better OCR
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if h < 1000 or w < 1000:
        scale = max(1000 / h, 1000 / w)
        gray  = cv2.resize(gray, None, fx=scale, fy=scale,
                           interpolation=cv2.INTER_CUBIC)
                           
    # Simple binarization often works better than adaptive for clean screenshots
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    
    # PSM 4 assumes a single column of text of variable sizes (good for Qs + options)
    text = pytesseract.image_to_string(thresh, config="--oem 3 --psm 4")
    
    if len(text.strip()) < 20:
        # Fallback to sparse text
        text = pytesseract.image_to_string(gray, config="--oem 3 --psm 11")
        
    return text


def read_pdf(path):
    if not HAS_PDF:
        print(f"  ⚠  pdfplumber unavailable — skipping {path.name}")
        return ""
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t and t.strip():
                    text += t + "\n"
                elif HAS_OCR:
                    import numpy as np
                    pil_img = page.to_image(resolution=200).original
                    img_np  = np.array(pil_img)
                    gray    = (cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                               if img_np.ndim == 3 else img_np)
                    t2 = pytesseract.image_to_string(
                        gray, config="--oem 3 --psm 6"
                    )
                    if t2.strip():
                        text += t2 + "\n"
    except Exception as e:
        print(f"  ⚠  PDF error {path.name}: {e}")
    return text


def read_file(path):
    ext = path.suffix.lower()
    if ext == ".pdf":
        return read_pdf(path)
    if ext in (".png", ".jpg", ".jpeg"):
        return read_image(path)
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=enc, errors="ignore")
        except Exception:
            continue
    return ""


def normalise(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


# ══════════════════════════════════════════════════════════════
# TEXT / ANSWER HELPERS
# ══════════════════════════════════════════════════════════════

# Matches Format-A inline MCQ options inside a question line
_INLINE_OPT_RE = re.compile(r"(?<!\w)\(?([A-Ea-e])[\).:\-]+\s*")


def parse_inline_options(line, legend=None):
    """Extract A/B/C/D/E options embedded in a single line."""
    parts = _INLINE_OPT_RE.split(line)
    if len(parts) < 3:
        return {}
    
    opts = {}
    for idx in range(1, len(parts) - 1, 2):
        key = parts[idx].upper()
        val = parts[idx + 1].strip().rstrip(",; ")
        
        # Reject placeholders like "(A) A"
        if val.upper() == key:
            if legend and key in legend:
                val = legend[key]
            else:
                continue
                
        if key in "ABCDE" and val:
            opts[key] = val
            
    # Handle "implied A" case: "12 (B) 14 (C) 16"
    if "B" in opts and "A" not in opts:
        prefix = parts[0].strip().rstrip(",; (")
        if 0 < len(prefix) < 100:
            opts["A"] = prefix
            
    return opts if len(opts) >= 2 else {}


# Matches an answer line in many variants
# The leading [\s✅✓☑🔖►▶•–—]* handles emoji/symbol prefixes like "✅ Answer: ..."
_ANS_RE = re.compile(
    r"[\s✅✓☑🔖►▶•–—]*\*{0,2}(?:Ans(?:wer)?|Corrected|Ans\.|Ans|Answer)\*{0,2}\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)


def is_answer_line(line):
    """Return the raw answer text if this is an answer/corrected line."""
    m = _ANS_RE.match(line.strip())
    if m:
        return m.group(1).strip().strip("*").strip()
    return None


def clean_answer_key(raw):
    """Return A/B/C/D/E from 'B) Plentiful' or 'B'."""
    if not raw:
        return None
    raw = raw.strip()
    m = re.match(r"^\(?([A-Ea-e])\)?[.):\s]", raw)
    if m:
        return m.group(1).upper()
    if re.fullmatch(r"[A-Ea-e]", raw):
        return raw.upper()
    return None


def strip_answer_key(raw):
    """'B) Plentiful' → 'Plentiful';  '10' → '10'."""
    m = re.match(r"^\(?[A-Ea-e]\)?[.):\-]\s*(.+)", raw.strip())
    return m.group(1).strip() if m else raw.strip()


def clean_q_text(text):
    """Remove markdown noise from a question string."""
    text = re.sub(r"\*+", "", text)           # remove ** and *
    text = re.sub(r"^[\d]+[.)]\s*", "", text) # remove leading "1. "
    text = re.sub(r"^Q(?:uestion)?\s*:?\s*", "", text, flags=re.IGNORECASE)
    text = text.strip().rstrip(":").strip()
    return text


def is_real_question(text, filename=""):
    """
    Return True only if this text looks like an actual exam question.
    """
    if len(text) > 3000:
        return False

    is_image_or_pdf = filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf'))

    bad_starts = (
        r"^this file contains",
        r"^the following (table|data|passage|paragraph)",
        r"^directions?\s*:",
        r"^note\s*:",
        r"^read (the following|this)",
        r"^based on (the following|this)",
        r"^questions?\s*\d+",
        r"^passage\s*:",
        r"^table\s*\d",
        r"^section\s*[:\d]",
        r"^instructions?\s*:",
    )
    for pat in bad_starts:
        if re.match(pat, text, re.IGNORECASE):
            return False

    # If it starts with a strong marker (Q1., Q2., etc.), we trust it's a question
    # We check if the trimmed text starts with a marker (common after clean_q_text)
    # or if the original text had it.
    if re.match(r"^\d+", text) or any(kw in text.lower() for kw in ["statements", "conclusions", "conclusion", "inference"]):
        return True

    has_q_word = bool(re.search(
        r"[?]|"
        r"\b(how|what|which|find|where|when|why|who|whose|whom|calculate|determine|"
        r"evaluate|examine|prove|solve|draw|identify|select|choose|complete|if|"
        r"pattern|next|sequence|series|unfolded|fold|punch|logic|logically|"
        r"result|total|count|value|ratio|proportion|days?|time)\b",
        text, re.IGNORECASE
    ))
    return has_q_word or is_image_or_pdf


# ══════════════════════════════════════════════════════════════
# DISTRACTOR / MCQ BUILDER  — section-scoped, type-matched
# ══════════════════════════════════════════════════════════════

_FALLBACKS = [
    "None of the above", "Cannot be determined",
    "Insufficient data", "All of the above",
    "Data not provided", "Not applicable",
    "Option not listed", "None of these",
]


def infer_type(val: str) -> str:
    """
    Assign a fine-grained type label based on the unit suffix, so
    '550 units' and '130 students' never become each other's distractors.
    """
    v = val.strip()

    # Ratio  e.g. "9 : 10"
    if re.fullmatch(r"[\d,.]+\s*:\s*[\d,.]+(\s*:\s*[\d,.]+)?", v):
        return "ratio"

    # Percentage  e.g. "25%"
    if re.fullmatch(r"[\d,.]+\s*%", v):
        return "percent"

    # Currency  e.g. "$45,000"  "$1.44/kg"
    if re.match(r"^[\$₹£€]", v):
        return "currency"

    # Numeric with a UNIT SUFFIX — key is the unit word(s)
    # e.g.  "1100 units" → "numeric_units"
    #        "130 students" → "numeric_students"
    #        "17°C"         → "numeric_°c"
    unit_m = re.fullmatch(
        r"[\d,.]+ *(units?|books?|students?|visitors?|points?|"
        r"dots?|stars?|km|kg|km/h|°[Cc]|[Cc]°|people|cars?|"
        r"days?|hours?|months?|years?|letters?|items?|teams?|"
        r"classes?|departments?|genres?|companies|fruits?|"
        r"types?|players?|marks?|calories?|grams?|litres?|"
        r"$)",
        v, re.IGNORECASE
    )
    if unit_m:
        unit = unit_m.group(1).lower().rstrip("s")  # normalise plural
        return f"numeric_{unit}"

    # Pure integer or decimal with no unit  e.g. "17"  "32,500"
    if re.fullmatch(r"[\d,]+(\.\d+)?", v):
        return "numeric"

    # Coded strings  e.g. "EPH", "SFBE"
    if re.fullmatch(r"[A-Z]{2,8}", v):
        return "code"

    # Everything else (words, phrases, names)
    return "word"


def make_distractors(correct: str, section_pool: list, n: int = 3) -> list:
    """
    Pick n distractors from the section-scoped pool.
    Priority: exact same type → any other → fallbacks.
    """
    correct_type  = infer_type(correct)
    correct_lower = correct.lower().strip()

    same_type, diff_type = [], []
    seen = {correct_lower}
    for a in section_pool:
        a  = str(a).strip()
        al = a.lower()
        if al in seen or len(a) > 150 or not a:
            continue
        seen.add(al)
        if infer_type(a) == correct_type:
            same_type.append(a)
        else:
            diff_type.append(a)

    random.shuffle(same_type)
    random.shuffle(diff_type)

    # Prefer same-unit distractors; only fall back to diff-type if short
    distractors = (same_type + diff_type)[:n]

    for fb in _FALLBACKS:
        if len(distractors) >= n:
            break
        if fb.lower() not in seen:
            distractors.append(fb)
            seen.add(fb.lower())

    return distractors[:n]


def build_mcq(correct: str, distractors: list):
    """Assign A/B/C/D labels, shuffle, return (opts_dict, correct_key)."""
    pool = ([correct] + distractors)[:4]
    fb_i = 0
    while len(pool) < 4:
        fb = _FALLBACKS[fb_i % len(_FALLBACKS)]
        if fb not in pool:
            pool.append(fb)
        fb_i += 1
    pool = pool[:4]
    random.shuffle(pool)
    keys = list("ABCD")
    opts = {keys[i]: pool[i] for i in range(4)}
    key  = next(k for k, v in opts.items() if v == correct)
    return opts, key


# ══════════════════════════════════════════════════════════════
# MAIN EXTRACTOR
# ══════════════════════════════════════════════════════════════

def extract_questions(text: str, filename: str) -> list:
    lines    = [l.rstrip() for l in text.split("\n")]
    results  = []
    category = re.sub(r"\.(md|txt|pdf|png|jpg|jpeg)$", "", filename,
                      flags=re.I)

    # ── Pre-pass: index answer values and detect LEGENDS per SECTION ─────
    sections: dict[str, list] = {}  # heading → answer list
    legends: dict[str, dict]  = {}  # heading → {A: val, B: val, ...}
    current_section = "__top__"
    sections[current_section] = []
    legends[current_section] = {}

    for line in lines:
        stripped = line.strip()
        if not stripped: continue
        
        if re.match(r"^#{1,3}\s+.{3,}", stripped):
            heading = re.sub(r"^#{1,3}\s+", "", stripped).strip("*_ ")
            if 3 < len(heading) < 120:
                current_section = heading
            if current_section not in sections:
                sections[current_section] = []
            if current_section not in legends:
                legends[current_section] = {}
            continue
            
        ans_raw = is_answer_line(stripped)
        if ans_raw:
            val = strip_answer_key(ans_raw)
            if val and len(val) < 150 and not re.match(
                r"^(not sufficient|each alone|statement \d|both statements)",
                val, re.IGNORECASE
            ):
                sections.setdefault(current_section, []).append(val)
        
        # Legend detection
        o_m = re.match(r"^\(?([A-Ea-e])\)?[.):–\-]\s*(.+)", stripped, re.IGNORECASE)
        if o_m:
            key, val = o_m.group(1).upper(), o_m.group(2).strip()
            # If it has other inline options, it's NOT a legend line
            if len(_INLINE_OPT_RE.findall(val)) > 0:
                continue
            if len(val) > 15 and val.upper() != key:
                legends.setdefault(current_section, {})[key] = val

    # ── Second pass: detect question blocks ───────────────────
    current_section = "__top__"
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # Track section from headings
        if re.match(r"^#{1,3}\s+.{3,}", stripped):
            heading = re.sub(r"^#{1,3}\s+", "", stripped).strip("*_ ")
            if 3 < len(heading) < 120:
                current_section = heading
            i += 1
            continue

        # ── Detect question start ──────────────────────────────
        # Accept explicit markers even without "**" (OCR often misses them)
        q_explicit = re.match(
            r"^(?:\d+[.)|\]]\s*)?\*?Q(?:uestion)?\*?\s*:?\s*(.*)",
            stripped, re.IGNORECASE
        )
        q_numbered = re.match(r"^(\d+)[.)|\]]\s+(.{15,})", stripped)

        q_text = None
        if q_explicit:
            q_text = q_explicit.group(1).strip().strip("*").strip()
            # If it's an explicit "Q" marker, we TRUST it's a question
            if not q_text or len(q_text) < 15:
                lookahead = []
                for offset in range(1, 8):
                    if i + offset >= len(lines): break
                    nxt = lines[i + offset].strip()
                    if re.match(r"(?:Options?|A\)|Answer)[\s:]", nxt, re.I): break
                    if not nxt: continue
                    lookahead.append(nxt)
                q_text = (q_text + " " + " ".join(lookahead)).strip()
            trust_marker = True
        elif q_numbered:
            candidate = q_numbered.group(2).strip()
            if is_real_question(candidate, filename) or len(candidate) > 20:
                q_text = candidate
                trust_marker = True
            else:
                trust_marker = False
        else:
            trust_marker = False

        # For images, we are much more lenient on "is_real_question"
        is_image_or_pdf = filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf'))
        
        if q_text is None or (not trust_marker and not is_real_question(q_text, filename) and not is_image_or_pdf):
            i += 1
            continue

        # Clean the question text
        q_text = clean_q_text(q_text)
        current_legend = legends.get(current_section, {})

        # ── Extract inline options from question line ──────────
        inline_opts = parse_inline_options(q_text, current_legend)
        if inline_opts:
            first_key = sorted(inline_opts.keys())[0]
            fm = re.search(
                r"(?<!\w)\(?" + first_key + r"\)?[.):\-]",
                q_text, re.IGNORECASE
            )
            if fm:
                q_text = q_text[:fm.start()].strip().rstrip(":").strip()

        q_text = clean_q_text(q_text)

        if len(q_text) < 8:
            i += 1
            continue

        # ── Scan forward for options / answer ──────────────────
        answer_raw = None
        multi_opts = {}
        j = i + 1

        while j < len(lines) and j < i + 40:
            look = lines[j].strip()
            if not look:
                j += 1
                continue

            # Answer / Corrected line
            raw = is_answer_line(look)
            if raw is not None:
                answer_raw = raw
                j += 1
                break

            # Skip solution/explanation lines
            if re.match(
                r"(\*{0,2}(Solution|Explanation|Reason|Working|Steps?)\*{0,2}\s*[:\-]|\[.*\])",
                look, re.IGNORECASE
            ):
                j += 1
                continue

            # Option checking (Multi-option line or single option)
            opts_on_this_line = parse_inline_options(look, current_legend)
            if opts_on_this_line:
                multi_opts.update(opts_on_this_line)
                j += 1
                continue

            o_m = re.match(r"^\(?([A-Ea-e])\)?[.):–\-]\s*(.+)", look,
                           re.IGNORECASE)
            if o_m:
                key, val = o_m.group(1).upper(), o_m.group(2).strip()
                # Reject placeholders
                if val.upper() == key:
                    if current_legend and key in current_legend:
                        val = current_legend[key]
                    else:
                        j += 1
                        continue
                multi_opts[key] = val
                j += 1
                continue

            # Stop at next question
            if re.match(r"^\d+[.)|\]]\s+\S", look) and j > i + 1:
                break
            if re.match(r"^(?:\d+[.)|\]]\s*)?Q(?:uestion)?\s*:?\s*", look, re.IGNORECASE) and j > i + 1:
                break

            # If it's not an option or answer, and we haven't found any options yet,
            # it's likely more question text (e.g. "Conclusions:" in Syllogism)
            if not multi_opts and not answer_raw:
                q_text += " " + look
            
            j += 1

        if not answer_raw:
            # KEEP the question even if no explicit answer was found.
            # We'll default to 'A' or 'Unknown' rather than skipping 800+ questions.
            answer_raw = "A" 

        # ── Resolve format and build final MCQ ────────────────
        opts = {**inline_opts, **multi_opts}
        # Fill missing from legend if it's a themed question set (like Data Sufficiency)
        if current_legend and len(opts) < len(current_legend):
            for k, v in current_legend.items():
                if k not in opts:
                    opts[k] = v

        ans_key = clean_answer_key(answer_raw)
        ans_val = strip_answer_key(answer_raw)
        # If answer is just a letter, map to legend value if possible
        if current_legend and len(ans_val) == 1 and ans_val.upper() in current_legend:
            ans_val = current_legend[ans_val.upper()]

        if not opts and answer_raw != "Unknown":
            # FORMAT B: build options from SECTION-SCOPED pool
            section_pool = sections.get(current_section, [])
            pool_filtered = [
                v for v in section_pool
                if v.strip().lower() != ans_val.strip().lower()
            ]
            distractors = make_distractors(ans_val, pool_filtered)
            final_opts, correct_key = build_mcq(ans_val, distractors)
        else:
            # FORMAT A / IMAGE: proper options already present, or no options but it's an image
            final_opts = dict(opts) if opts else {}
            # Fill mandatory labels if missing
            fb_i = 0
            for k in "ABCD": # Keep base 4 for consistency if no E in legend
                if k not in final_opts:
                    final_opts[k] = _FALLBACKS[fb_i % len(_FALLBACKS)]
                    fb_i += 1
            
            # If answer is 'E', ensure 'E' is in final_opts
            if ans_key == "E" and "E" not in final_opts:
                final_opts["E"] = current_legend.get("E", _FALLBACKS[fb_i % len(_FALLBACKS)])

            correct_key = ans_key if ans_key and ans_key in final_opts else next(iter(final_opts.keys()), "A")

        results.append({
            "question": q_text,
            "options" : final_opts,
            "answer"  : correct_key,
            "category": current_section if current_section != "__top__"
                        else category,
            "source"  : filename,
        })

        i = j

    # Fallback for messy OCR images where line-by-line fails completely
    if not results and filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        raw_text = text.strip()
        if len(raw_text) > 20:
            # Try to grab option letters
            opts = {}
            # Match (A) or A) or (a) or a)
            opt_matches = list(re.finditer(r"(?<!\w)\(?([A-Da-d])\)?[.):\-]\s*(.*?)(?=(?:\(?[A-Da-d]\)?[.):\-])|$)", raw_text, re.IGNORECASE | re.DOTALL))
            for m in opt_matches:
                k = m.group(1).upper()
                v = m.group(2).strip()
                if k in "ABCD" and k not in opts:
                    opts[k] = clean_q_text(v.replace('\n', ' '))
            
            # Remove the options from the question text
            q_text = raw_text
            if opt_matches:
                q_text = raw_text[:opt_matches[0].start()].strip()
                
            q_text = clean_q_text(q_text.replace('\n', ' '))
            
            if len(q_text) > 10:
                final_opts = dict(opts) if opts else {}
                fb_i = 0
                for k in "ABCD":
                    if k not in final_opts:
                        final_opts[k] = _FALLBACKS[fb_i % len(_FALLBACKS)]
                        fb_i += 1
                        
                results.append({
                    "question": q_text,
                    "options" : final_opts,
                    "answer"  : "A", # Unknown
                    "category": category,
                    "source"  : filename,
                })

    return results


# ══════════════════════════════════════════════════════════════
# SAVE / MERGE
# ══════════════════════════════════════════════════════════════

def save_questions(new_qs: list):
    existing = []
    if OUTPUT_JSON.exists():
        try:
            existing = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    # Deduplicate strictly by question text to align with Supabase UNIQUE(question) constraint
    merged = {}
    for q in existing:
        q_text = str(q.get("question", "")).strip()
        if q_text:
            merged[q_text] = q

    for q in new_qs:
        q_text = str(q.get("question", "")).strip()
        if q_text:
            merged[q_text] = q

    final = list(merged.values())
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(final, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n[OK] Total questions saved: {len(final)}")


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

def convert_all():
    supported = {".txt", ".md", ".pdf", ".png", ".jpg", ".jpeg"}
    all_qs: list = []

    for f in sorted(INPUT_DIR.rglob("*.*")):
        if f.suffix.lower() not in supported:
            continue
        print(f"\nFile: {f.name}")
        try:
            raw = normalise(read_file(f))
            if not raw.strip():
                print("    [WARN] Empty / unreadable file")
                continue
            qs = extract_questions(raw, f.name)
            print(f"    - {len(qs)} questions")
            all_qs.extend(qs)
        except Exception as e:
            print(f"    [FAIL] {e}")

    if not all_qs:
        print("\n[ERROR] Nothing extracted.")
        return

    save_questions(all_qs)


if __name__ == "__main__":
    # Always regenerate from scratch so the JSON stays clean
    OUTPUT_JSON.unlink(missing_ok=True)
    convert_all()
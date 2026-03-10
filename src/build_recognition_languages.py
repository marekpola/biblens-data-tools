import json
import re
import unicodedata
from pathlib import Path

from osis_to_usfm import OSIS_TO_USFM

INPUT_DIR = Path("data/raw/openbibleinfo/lang")
OUTPUT_DIR = Path("data/generated/recognition-languages")


BOOK_ORDER = [
    "GEN","EXO","LEV","NUM","DEU",
    "JOS","JDG","RUT",
    "1SA","2SA","1KI","2KI","1CH","2CH",
    "EZR","NEH","EST","JOB","PSA","PRO","ECC","SNG",
    "ISA","JER","LAM","EZK","DAN",
    "HOS","JOL","AMO","OBA","JON","MIC","NAM","HAB","ZEP","HAG","ZEC","MAL",
    "MAT","MRK","LUK","JHN","ACT",
    "ROM","1CO","2CO","GAL","EPH","PHP","COL",
    "1TH","2TH","1TI","2TI","TIT","PHM",
    "HEB","JAS","1PE","2PE","1JN","2JN","3JN","JUD","REV",
    "TOB","JDT","ESG","WIS","SIR","BAR","LJE","S3Y","SUS","BEL",
    "1MA","2MA","3MA","4MA",
    "1ES","2ES",
    "MAN","PS2","ODA","PSS",
    "EZA","5EZ","6EZ",
    "DAG","PS3",
    "2BA","LBA",
    "JUB","ENO",
    "1MQ","2MQ","3MQ",
    "REP","4BA",
    "LAO",
]


# None = build all downloaded languages
# Example: ONLY_LANGS = {"ces"}
ONLY_LANGS ={"deu"}

LANG_ID_MAP = {
    "ces": "cs",
    "eng": "en",
    "deu": "de",
    "fra": "fr",
    "spa": "es",
    "ita": "it",
    "por": "pt",
    "pol": "pl",
    "slk": "sk",
    "slv": "sl",
    "nld": "nl",
    "ron": "ro",
    "hun": "hu",
    "lat": "la",
    "grc": "grc",
    "heb": "he",
}

DISPLAY_NAME_MAP = {
    "cs": "Czech",
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "pl": "Polish",
    "sk": "Slovak",
    "sl": "Slovene",
    "nl": "Dutch",
    "ro": "Romanian",
    "hu": "Hungarian",
    "la": "Latin",
    "grc": "Greek",
    "he": "Hebrew",
}

BOOK_ENTRY_RE = re.compile(
    r'osis\s*:\s*\[(?P<osis>[^\]]+)\].*?regexp\s*:\s*/(?P<regex>(?:\\.|[^/])*)/(?P<flags>[a-z]*)',
    re.DOTALL
)

QUOTED_STRING_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')





def map_lang_id(source_lang_id: str) -> str:
    return LANG_ID_MAP.get(source_lang_id, source_lang_id)


def display_name_for(lang_id: str) -> str:
    return DISPLAY_NAME_MAP.get(lang_id, lang_id)


def find_matching_paren(text: str, start: int) -> int:
    depth = 0
    escaped = False

    for i in range(start, len(text)):
        ch = text[i]

        if escaped:
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue

        if ch == "(":
            depth += 1
            continue

        if ch == ")":
            depth -= 1
            if depth == 0:
                return i

    return -1


def expand_simple_pattern(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []

    # Normalize a few common regex constructs first
    text = re.sub(r"\\s[\*\+\?]?", " ", text)
    text = re.sub(r"\[([^\]]+)\]", lambda m: first_char_from_class(m.group(1)), text)

    text = text.replace(r"\.", ".")
    text = text.replace(r"\:", ":")
    text = text.replace(r"\,", ",")
    text = text.replace(r"\/", "/")
    text = text.replace(r"\-", "-")
    text = text.replace(r"\(", "(")
    text = text.replace(r"\)", ")")

    # Split top-level alternatives first, before expanding any group.
    # Without this, the suffix of a (?:...) expansion can contain a raw "|",
    # which ends up literally embedded in the produced alias strings.
    top_alts = split_top_level_alternatives(text)
    if len(top_alts) > 1:
        variants = []
        for alt in top_alts:
            variants.extend(expand_simple_pattern(alt))
        return variants

    # Expand first non-capturing group
    start = text.find("(?:")
    if start != -1:
        end = find_matching_paren(text, start)
        if end != -1:
            inside = text[start + 3:end]
            options = split_top_level_alternatives(inside)
            optional = end + 1 < len(text) and text[end + 1] == "?"

            prefix = text[:start]
            suffix = text[end + 2:] if optional else text[end + 1:]

            variants = []
            if optional:
                variants.extend(expand_simple_pattern(prefix + suffix))

            for option in options:
                variants.extend(expand_simple_pattern(prefix + option + suffix))

            return variants

    # Expand simple optional character: x?
    m = re.search(r"([^\\])\?", text)
    if m:
        i = m.start()
        variants = []
        variants.extend(expand_simple_pattern(text[:i] + text[i] + text[i + 2:]))
        variants.extend(expand_simple_pattern(text[:i] + text[i + 2:]))
        return variants

    return [text]



def extract_book_core(regex_body: str) -> str | None:
    escaped = False
    start = None

    i = 0
    while i < len(regex_body):
        ch = regex_body[i]

        if escaped:
            escaped = False
            i += 1
            continue

        if ch == "\\":
            escaped = True
            i += 1
            continue

        if ch == "(":
            next_char = regex_body[i + 1] if i + 1 < len(regex_body) else ""
            if next_char != "?":
                start = i
                break

        i += 1

    if start is None:
        return None

    depth = 0
    escaped = False

    for i in range(start, len(regex_body)):
        ch = regex_body[i]

        if escaped:
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue

        if ch == "(":
            depth += 1
            continue

        if ch == ")":
            depth -= 1
            if depth == 0:
                return regex_body[start + 1:i]

    return None


def split_top_level_alternatives(text: str) -> list[str]:
    parts = []
    current = []
    depth_paren = 0
    depth_bracket = 0
    escaped = False

    for ch in text:
        if escaped:
            current.append(ch)
            escaped = False
            continue

        if ch == "\\":
            current.append(ch)
            escaped = True
            continue

        if ch == "(":
            depth_paren += 1
            current.append(ch)
            continue

        if ch == ")":
            depth_paren = max(0, depth_paren - 1)
            current.append(ch)
            continue

        if ch == "[":
            depth_bracket += 1
            current.append(ch)
            continue

        if ch == "]":
            depth_bracket = max(0, depth_bracket - 1)
            current.append(ch)
            continue

        if ch == "|" and depth_paren == 0 and depth_bracket == 0:
            part = "".join(current)
            if part.strip():
                parts.append(part)
            current = []
            continue

        current.append(ch)

    tail = "".join(current)
    if tail.strip():
        parts.append(tail)

    return parts


def unwrap_outer_group(text: str) -> str:
    text = text.strip()
    changed = True

    while changed:
        changed = False
        if text.startswith("(?:") and text.endswith(")"):
            text = text[3:-1].strip()
            changed = True
        elif text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()
            changed = True

    return text


def first_char_from_class(content: str) -> str:
    content = content.replace("\\", "")
    return content[0] if content else ""


def clean_alias(part: str) -> str | None:
    s = part.strip()
    if not s:
        return None

    s = unwrap_outer_group(s)

    # Skip lookarounds and other constructs that are not real aliases.
    if "(?=" in s or "(?!" in s or "(?<" in s:
        return None

    # Common regex prefixes/suffixes around book names.
    s = s.replace("^", "")
    s = s.replace("$", "")
    s = s.replace(r"\b", "")
    s = s.replace(r"\xa0", " ")
    s = s.replace(r"\u00a0", " ")

    # Space-like constructs.
    s = re.sub(r"\\s[\*\+\?]?", " ", s)

    # Optional punctuation/characters: keep the base form.
    s = s.replace(r"\.?", ".")
    s = s.replace(r"\. ", ". ")
    s = s.replace(r"\.", ".")
    s = s.replace(r"\:", ":")
    s = s.replace(r"\,", ",")
    s = s.replace(r"\/", "/")
    s = s.replace(r"\-", "-")
    s = s.replace(r"\(", "(")
    s = s.replace(r"\)", ")")

    # Character classes like [nň] -> n
    s = re.sub(r"\[([^\]]+)\]", lambda m: first_char_from_class(m.group(1)), s)

    # Simple optional char: a? -> a
    s = re.sub(r"([^\s])\?", r"\1", s)

    # Remove remaining non-capturing groups if any.
    s = s.replace("(?:", "")
    s = s.replace("(", "")
    s = s.replace(")", "")

    # Remove remaining backslashes.
    s = s.replace("\\", "")

    # Normalize spaces.
    s = re.sub(r"\s+", " ", s).strip()

    # Skip obvious regex leftovers.
    if not s:
        return None
    if any(token in s for token in ["{", "}", "*", "+"]):
        return None

    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")

    return s


def parse_osis_list(raw_osis: str) -> list[str]:
    values = []
    for match in QUOTED_STRING_RE.finditer(raw_osis):
        value = match.group(1) or match.group(2)
        if value:
            values.append(value)
    return values


def extract_aliases_from_regex(regex_body: str) -> list[str]:
    core = extract_book_core(regex_body)
    if not core:
        return []

    core = unwrap_outer_group(core)

    expanded = expand_simple_pattern(core)

    aliases = []
    for part in expanded:
        alias = clean_alias(part)
        if alias:
            aliases.append(alias)

    aliases, _ = unique_keep_order(aliases)
    return aliases

def unique_keep_order(items: list[str]) -> tuple[list[str], int]:
    seen = set()
    result = []
    removed = 0

    for item in items:
        key = item.casefold()
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        result.append(item)

    return result, removed

def order_books(books: dict) -> dict:
    ordered = {}

    for book_id in BOOK_ORDER:
        if book_id in books:
            ordered[book_id] = books[book_id]

    # případné neznámé knihy na konec
    for book_id in books:
        if book_id not in ordered:
            ordered[book_id] = books[book_id]

    return ordered


def parse_books(js_text: str) -> tuple[dict[str, list[str]], list[str], int]:
    books: dict[str, list[str]] = {}
    warnings: list[str] = []
    duplicate_count = 0

    for match in BOOK_ENTRY_RE.finditer(js_text):
        osis_values = parse_osis_list(match.group("osis"))
        #print("FOUND:", osis_values[:3], match.group("regex")[:80])
        regex_body = match.group("regex")

        aliases = extract_aliases_from_regex(regex_body)
        if not aliases:
            continue

        for osis_id in osis_values:
            usfm = OSIS_TO_USFM.get(osis_id)
            if not usfm:
                warnings.append(f"Unknown OSIS id: {osis_id}")
                continue

            existing = books.get(usfm, [])
            merged, removed = unique_keep_order(existing + aliases)
            books[usfm] = merged
            duplicate_count += removed

    return books, warnings, duplicate_count


def build_language_pack(source_file: Path) -> tuple[dict, list[str], int]:
    source_lang_id = source_file.stem
    lang_id = map_lang_id(source_lang_id)
    display_name = display_name_for(lang_id)

    js_text = source_file.read_text(encoding="utf-8")
    books, warnings, duplicate_count = parse_books(js_text)

    ordered_books = order_books({
        book_id: {"aliases": aliases}
        for book_id, aliases in books.items()
    })

    data = {
        "id": lang_id,
        "displayName": display_name,
        "lang": lang_id,
        "formatVersion": 1,
        "source": f"openbibleinfo/Bible-Passage-Reference-Parser-Languages/lang/{source_file.name}",
        "books": ordered_books,
    }

    return data, warnings, duplicate_count


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_files = sorted(INPUT_DIR.glob("*.js"))
    if ONLY_LANGS:
        source_files = [p for p in source_files if p.stem in ONLY_LANGS]

    total_files = 0
    total_books = 0
    total_aliases = 0
    total_duplicates = 0
    total_warnings = 0

    for source_file in source_files:
        data, warnings, duplicate_count = build_language_pack(source_file)

        out_file = OUTPUT_DIR / f"{data['id']}.json"
        out_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        book_count = len(data["books"])
        alias_count = sum(len(item["aliases"]) for item in data["books"].values())

        total_files += 1
        total_books += book_count
        total_aliases += alias_count
        total_duplicates += duplicate_count
        total_warnings += len(warnings)

        print(f"OK   {source_file.name} -> {out_file.name}")
        print(f"     books: {book_count}, aliases: {alias_count}, duplicates removed: {duplicate_count}")

        if warnings:
            print(f"     warnings: {len(warnings)}")
            for warning in warnings[:5]:
                print(f"       - {warning}")
            if len(warnings) > 5:
                print(f"       - ... and {len(warnings) - 5} more")

    print()
    print("Finished")
    print(f"Files: {total_files}")
    print(f"Books: {total_books}")
    print(f"Aliases: {total_aliases}")
    print(f"Duplicates removed: {total_duplicates}")
    print(f"Warnings: {total_warnings}")


if __name__ == "__main__":
    main()
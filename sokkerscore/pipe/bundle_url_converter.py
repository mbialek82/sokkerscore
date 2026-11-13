"""
bundle_url_converter_v2.py

Convert older Sokker match_video bundles (URL-encoded query-string format)
to the newer JSON container format the existing bundle_decoder_v4 expects.

v2 fix (April 2026): the char-to-byte conversion was wrong for ord >= 97
(lowercase letters). The original code did `(ord(c) - 48) & 0xFF` for
every character, but the live Sokker viewer at
files.sokker.org/viewer-2d/bundle.js uses a piecewise function:

    flashByte(t) = t < 97 ? t - 48 : t - 97 + 43

So lowercase chars 'a'..'z' (ord 97..122) decode to bytes 43..68, NOT
49..74 as the old code produced. Every byte from a lowercase char was
six too high, causing all coordinates to drift systematically off-pitch.
This was the single bug responsible for 0/28 bundles producing sane
ball coordinates in earlier diagnostics.

Old format: pitchwidth=72&pitchheight=102&...&Ball=<string>&Human0=<string>&...
  - Each key=value pair separated by &
  - Metadata values (pitchwidth, TeamA_Name, etc.) are plain scalars
  - Stream values (Ball, Human0..Human21, Score) are Flash-encoded character
    strings, where each character's ord() is the raw byte value the decoder needs.

New format: {"_data": [{"name": ..., "tab": {"data": [int, int, ...]}}], "_vars": [{"name": ..., "value": ...}]}

The conversion is lossless for our purposes: we split meta vs stream keys,
turn stream strings into int-arrays, and emit the JSON shape.

Usage
-----
    python3 bundle_url_converter_v1.py <input_url_encoded.json> <output_json.json>

Or as a library:
    from bundle_url_converter_v1 import convert_file
    convert_file('43031346.json', '43031346_converted.json')
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote_plus

# Keys that carry binary stream data (need string → int-array conversion)
STREAM_PREFIXES = ('Ball', 'Human', 'Score')
# But some Human_xxx keys are metadata (Human_namea*, Human_nameb*, etc.)
STREAM_METADATA_PREFIXES = (
    'Human_namea', 'Human_nameb', 'Human_nameA', 'Human_nameB',
    'Human_skilla', 'Human_skillb', 'Human_skillA', 'Human_skillB',
    'Human_number', 'Human_photo', 'Human_face',
)


def is_stream_key(key: str) -> bool:
    """True if this key holds a binary stream (Ball / Humani / Score)."""
    if not key.startswith(STREAM_PREFIXES):
        return False
    if any(key.startswith(p) for p in STREAM_METADATA_PREFIXES):
        return False
    # Human0 .. Human21 are streams; Human_namea0 etc. are metadata
    if key.startswith('Human') and not key[5:].isdigit():
        return False
    return True


def flash_byte(c: str) -> int:
    """Char-to-byte conversion matching the live Sokker viewer.

    The viewer's bundle.js defines:
        flashByte(t) = t < 97 ? t - 48 : t - 97 + 43
    so chars in the lowercase range get a different offset than the rest.
    This is the corrected version of the original `(ord(c) - 48) & 0xFF`,
    which was off by 6 for every lowercase character.
    """
    n = ord(c)
    return n - 48 if n < 97 else n - 54  # n - 97 + 43 == n - 54


def convert_bundle_text(raw: str) -> dict:
    """Convert URL-encoded bundle text to the _data/_vars JSON structure."""
    # parse_qs returns lists; we take first value per key.
    parsed = parse_qs(raw, max_num_fields=100000, keep_blank_values=True)
    flat: dict[str, str] = {k: v[0] for k, v in parsed.items() if v}

    _data = []
    _vars = []
    for key, val in flat.items():
        if is_stream_key(key):
            # Stream: convert character-string → list[int] of raw byte values
            # using the piecewise flashByte function the live viewer uses.
            _data.append({
                'name': key,
                'tab': {'data': [flash_byte(c) for c in val]},
            })
        else:
            # Metadata var
            _vars.append({'name': key, 'value': val})

    return {'_data': _data, '_vars': _vars}


def convert_file(input_path: str, output_path: str) -> dict:
    """Read a URL-encoded bundle from disk, write the JSON-form bundle. Returns the dict."""
    raw = Path(input_path).read_text(encoding='utf-8').strip()
    bundle = convert_bundle_text(raw)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(bundle, f)
    return bundle


def auto_convert_if_needed(input_path: str) -> str:
    """If the bundle at input_path is URL-encoded, convert it to a temp JSON
    file and return the new path. If it's already JSON, return input_path
    unchanged. For use inside the batch ingest pipeline."""
    raw = Path(input_path).read_text(encoding='utf-8').strip()
    if raw.startswith('{'):
        return input_path  # Already JSON form
    # Looks URL-encoded; convert and write alongside
    out_path = str(Path(input_path).with_suffix('.converted.json'))
    bundle = convert_bundle_text(raw)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(bundle, f)
    return out_path


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python3 bundle_url_converter_v1.py <in_url_encoded> <out_json>')
        sys.exit(1)
    convert_file(sys.argv[1], sys.argv[2])
    print(f'Converted {sys.argv[1]} → {sys.argv[2]}')

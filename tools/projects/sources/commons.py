"""Photographs are per-file reviewed manifests, never a blanket Commons licence."""
import hashlib
import json
import re
SOURCE = 'commons'
ALLOWED = r'(?:CC0 1\.0|CC BY(?:-SA)? (?:1\.0|2\.0|2\.5|3\.0|4\.0))'
def validate(photo, globe):
    if not photo or not re.fullmatch(ALLOWED, photo.get('licence', '')): return False
    if not photo.get('author') or not photo.get('source_url', '').startswith('https://commons.wikimedia.org/wiki/File:'): return False
    path = (globe / photo.get('file', '')).resolve()
    if not path.is_relative_to(globe.parent.resolve()) or not path.is_file(): return False
    return hashlib.sha256(path.read_bytes()).hexdigest() == photo.get('sha256')
def parse(path, spec):
    # Featured records are validated separately; images never generate map locations.
    return []

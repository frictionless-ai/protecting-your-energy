"""Owner identity supplied explicitly by the local operator."""
import json
import os

OWNER_ID = os.environ.get('THOUGHT_RECONSTRUCTION_OWNER_ID', '').strip()

try:
    aliases = json.loads(os.environ.get('THOUGHT_RECONSTRUCTION_OWNER_ALIASES', '[]'))
except json.JSONDecodeError as error:
    raise ValueError('THOUGHT_RECONSTRUCTION_OWNER_ALIASES must be a JSON array of names') from error
if not isinstance(aliases, list) or any(not isinstance(name, str) or not name.strip() for name in aliases):
    raise ValueError('THOUGHT_RECONSTRUCTION_OWNER_ALIASES must contain nonempty names')
OWNER_ALIASES = frozenset(name.strip().casefold() for name in aliases)

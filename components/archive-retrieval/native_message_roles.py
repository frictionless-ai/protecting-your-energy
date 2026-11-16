"""Pure Codex transport-role qualification; no actor or adoption proof."""
from __future__ import annotations

import json
import re


CONTROL_KINDS = frozenset((
    'agents_md.instructions', 'environments.environment_context',
    'additional_content.codex_apps_open_page', 'goal.internal_context', 'user.heartbeat',
))
MACHINE_ROLES = frozenset(('system', 'developer', 'assistant', 'tool', 'function'))
_GOAL = re.compile(r'<codex_internal_context\s+source\s*=\s*([\"\'])goal\1\s*>')
_BROWSER = re.compile(r'<in-app-browser-context(?:\s+source\s*=\s*([\"\'])ambient-ui-state\1)?\s*>')
# Legacy expansions are qualified from their complete structured header only.
# This label is a text-shape category, never an inferred native kind declaration.
_SKILL = re.compile(
    r'<skill>\r?\n<name>[A-Za-z0-9][A-Za-z0-9_.:-]*</name>\r?\n'
    r'<path>/[^<>\r\n]+/SKILL\.md</path>\r?\n')
_WRAPPERS = (
    (_GOAL, '</codex_internal_context>', 'goal.internal_context', '<codex_internal_context'),
    (_BROWSER, '</in-app-browser-context>', 'additional_content.codex_apps_open_page', '<in-app-browser-context'),
    (_SKILL, '</skill>', 'legacy-structured-skill-expansion', '<skill>'),
)



def _text(message):
    content = message.get('content')
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        values = []
        for item in content:
            value = item if isinstance(item, str) else (
                item.get('text') or item.get('content') or '') if isinstance(item, dict) else ''
            if isinstance(value, str) and value:
                values.append(value)
        return '\n'.join(values)
    return ''


def _object(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    if len(value) > 65536:
        return None
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError('duplicate-native-metadata-key')
            result[key] = item
        return result
    def constant(_):
        raise ValueError('nonfinite-native-metadata')
    try:
        result = json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError, RecursionError):
        return None
    return result if isinstance(result, dict) else None


def _declared_kinds(message, raw):
    """Only explicit retained native transport fields, never normalized role."""
    candidates = []
    for container in (message, raw):
        if 'internal_chat_message_metadata_passthrough' in container:
            meta = _object(container['internal_chat_message_metadata_passthrough'])
            if meta is None or 'content_item_kinds' not in meta:
                return None, 'invalid-retained-native-kind-metadata'
            candidates.append(meta['content_item_kinds'])
    event = raw.get('codex_event')
    if isinstance(event, dict) and isinstance(event.get('payload'), dict):
        payload = event['payload']
        if 'internal_chat_message_metadata_passthrough' in payload:
            meta = _object(payload['internal_chat_message_metadata_passthrough'])
            if meta is None or 'content_item_kinds' not in meta:
                return None, 'invalid-retained-native-kind-metadata'
            candidates.append(meta['content_item_kinds'])
    # Exact preservation contract; it describes a declared kind, not origin.
    status = raw.get('codex_native_content_item_kinds_status')
    if status is not None:
        if status != 'valid':
            return None, ('native-kind-metadata-not-preserved' if status == 'missing'
                          else 'invalid-retained-native-kind-metadata')
        candidates.append(raw.get('codex_native_content_item_kinds'))
    if not candidates:
        return None, 'native-kind-metadata-not-preserved'
    if any(not isinstance(value, list) or not 0 < len(value) <= 64
           or any(not isinstance(kind, str) or not 0 < len(kind) <= 256 for kind in value) for value in candidates):
        return None, 'invalid-retained-native-kind-metadata'
    if any(value != candidates[0] for value in candidates[1:]):
        return None, 'conflicting-retained-native-kind-metadata'
    return candidates[0], 'retained-native-content-item-kinds; original origin not verified'


def _leading_controls(text):
    """Recognize complete leading known wrappers, not arbitrary prose mentions."""
    cursor, found = 0, []
    while True:
        start = cursor
        while start < len(text) and text[start].isspace():
            start += 1
        match = None
        for pattern, closing, kind, opening in _WRAPPERS:
            match = pattern.match(text, start)
            if match is not None:
                break
        if match is None:
            break
        end = text.find(closing, match.end())
        if end < 0:
            break
        # A nested opening of the same wrapper makes simple closure ambiguous.
        if not text[match.end():end].strip() or opening in text[match.end():end]:
            break
        end += len(closing)
        found.append({'kind': kind, 'character_range': [start, end]})
        cursor = end
    return found, bool(text[cursor:].strip())


def _finish(result):
    result['effective_input_attribution_class'] = None
    result['effective_role'] = None
    if not result['owner_evidence_eligible']:
        result['effective_input_attribution_class'] = 'command_control'
        result['effective_role'] = 'meta'
    elif result['control_kind'] is not None or result['control_spans']:
        # Whole-message evidence is mixed; genuine prose remains available as
        # context without asserting all-span personal authorship.
        result['effective_input_attribution_class'] = 'unconfirmed_input'
        result['effective_role'] = 'meta'
    return result


def classify_native_message(message, platform):
    """Eligibility means not excluded as control, never confirmed owner identity.

    Codex kind declarations qualify the retained transport category only. Legacy
    text falls back to complete leading known wrappers. Human introductions,
    quoted wrappers and mixed prose are retained with uncertainty. Character
    ranges refer to the full normalized message, not an indexed chunk.
    """
    result = {'owner_evidence_eligible': True, 'classification': 'not-recognized-control',
              'control_kind': None, 'basis': 'no control category established',
              'original_origin_verified': False, 'control_spans': [],
              'authorship_or_adoption_verified': False, 'quoted_control_context_present': False,
              'declared_native_control_mixture': False,
              'owner_evidence_scope': 'Eligibility does not establish authorship; exclude control_spans from personal idea counts.'}
    if platform != 'codex':
        result.update(classification='outside-codex-transport-policy',
                      basis='no unsupported platform category inferred')
        return _finish(result)
    if not isinstance(message, dict):
        result.update(classification='unclassified-native-message', basis='message object unavailable')
        return _finish(result)
    extra = message.get('extra')
    raw = extra.get('raw', {}) if isinstance(extra, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    role = raw.get('codex_role')
    if isinstance(role, str) and role in MACHINE_ROLES:
        result.update(owner_evidence_eligible=False, classification='declared-native-machine-role',
                      control_kind='machine-role', basis='retained codex_role; original origin not verified')
        return _finish(result)
    kinds, kind_basis = _declared_kinds(message, raw)
    result['basis'] = kind_basis
    if kinds is not None and all(kind in CONTROL_KINDS for kind in kinds):
        result.update(owner_evidence_eligible=False, classification='declared-native-control',
                      control_kind=';'.join(dict.fromkeys(kinds)))
        return _finish(result)
    if kinds is not None and any(kind in CONTROL_KINDS for kind in kinds):
        result.update(classification='mixed-declared-native-content',
                      control_kind=';'.join(dict.fromkeys(kind for kind in kinds if kind in CONTROL_KINDS)),
                      declared_native_control_mixture=True)
    text = _text(message)
    spans, remainder = _leading_controls(text)
    if spans:
        result['control_spans'] = spans
        result['control_kind'] = ';'.join(dict.fromkeys(span['kind'] for span in spans))
        result['basis'] += '; complete leading known wrapper; human paste does not establish behavioral prose'
        result['classification'] = 'mixed-leading-control-and-prose' if remainder else 'complete-leading-native-control'
        result['owner_evidence_eligible'] = remainder
    elif kinds == ['user.text']:
        result['classification'] = 'declared-user-text; authorship-unverified'
    elif kinds is None:
        result['basis'] += '; no complete leading known wrapper; quoted or ordinary prose retained'
    embedded = []
    for opening, closing, kind, tag in _WRAPPERS:
        for match in opening.finditer(text):
            end = text.find(closing, match.end())
            if end >= 0 and text[match.end():end].strip() and tag not in text[match.end():end]:
                embedded.append({'kind': kind, 'character_range': [match.start(), end + len(closing)],
                                 'scope': 'embedded quoted control; not personal behavioral prose'})
    if embedded:
        known = {tuple(span['character_range']): span for span in result['control_spans']}
        known.update({tuple(span['character_range']): span for span in embedded})
        result['control_spans'] = sorted(known.values(), key=lambda span: span['character_range'])
        result['quoted_control_context_present'] = any(
            tuple(span['character_range']) not in {tuple(item['character_range']) for item in spans}
            for span in embedded)
        result['basis'] += '; complete embedded wrapper retained; quoted-span authorship unverified'
        if result['control_kind'] is None:
            result['classification'] = 'quoted-native-control-in-prose'
    return _finish(result)


def classify_native_span(message, platform, start=0, end=None):
    """Apply the same policy to exact full-message Python character coordinates."""
    text = _text(message) if isinstance(message, dict) else ''
    end = len(text) if end is None else end
    if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(text):
        raise ValueError('native-policy-character-range-invalid')
    result = classify_native_message(message, platform)
    result['matched_character_range'] = [start, end]
    intervals = sorted((max(start, span['character_range'][0]), min(end, span['character_range'][1]))
                       for span in result['control_spans']
                       if max(start, span['character_range'][0]) < min(end, span['character_range'][1]))
    merged = []
    for left, right in intervals:
        if merged and left <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], right)
        else:
            merged.append([left, right])
    count = sum(right - left for left, right in merged)
    result['matched_control_ranges'] = merged
    result['matched_control_characters'] = count
    result['matched_noncontrol_characters'] = end - start - count
    if result['owner_evidence_eligible'] and count:
        if count == end - start:
            result.update(owner_evidence_eligible=False, classification='matched-native-control-span',
                          effective_input_attribution_class='command_control', effective_role='meta')
        else:
            result.update(classification='matched-mixed-native-control-and-prose',
                          effective_input_attribution_class='unconfirmed_input', effective_role='meta')
    elif result['owner_evidence_eligible'] and result['control_spans'] and not count:
        # Structural wrapper ranges can locate surrounding prose. A declared
        # mixed transport category alone cannot safely map its other blocks.
        if not result.get('declared_native_control_mixture'):
            result.update(classification='matched-noncontrol-prose; authorship-unverified',
                          effective_input_attribution_class=None, effective_role=None)
    return result

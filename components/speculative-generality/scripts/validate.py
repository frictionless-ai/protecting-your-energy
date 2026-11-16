#!/usr/bin/env python3
"""Offline checks for this package; not a host validator or an LLM evaluator.

Python 3.9+; standard library only. Frontmatter values deliberately use JSON
scalars/arrays, a small valid YAML subset. Arbitrary YAML is not supported here.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlsplit

SKILLS = {'plan', 'build', 'review'}
AGENTS = {'future-scout', 'extension-architect', 'contract-challenger'}
READ_TOOLS = {'Read', 'Grep', 'Glob'}
DENIED = {'Bash', 'Edit', 'Write', 'NotebookEdit'}
ROOT_REF = re.compile(r'\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9._/-]+)')
LOCAL_LINK = re.compile(r'\[[^\]\n]*\]\(([^)\s]+)\)')
ROLE_REF = re.compile(r'\bspeculative-generality:([a-z][a-z-]+)\b')
KEY = re.compile(r'[A-Za-z][A-Za-z0-9_-]*\Z')
REQUIRED = {
    '.claude-plugin/plugin.json', 'README.md', 'LICENSE', 'PORTABILITY.md',
    'INTEGRATION.md', 'rules/policy.md', 'rules/protocol.md',
    'rules/verification.md', 'templates/handoff.md', 'templates/plan.md',
    'scripts/validate.py',
}


@dataclass
class Report:
    checks: int = 0
    errors: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def check(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.errors.append(message)

    def as_dict(self) -> dict[str, Any]:
        return {'status': 'PASS' if not self.errors else 'FAIL',
                'checks': self.checks, 'counts': self.counts,
                'errors': self.errors,
                'scope': 'Offline package structure, not native loading or model behavior'}


def frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse only the authored JSON-valued YAML subset, rejecting ambiguity."""
    lines = text.splitlines()
    if not lines or lines[0] != '---':
        raise ValueError('frontmatter must start at the first line')
    try:
        end = lines.index('---', 1)
    except ValueError as exc:
        raise ValueError('frontmatter closing delimiter is missing') from exc
    fields: dict[str, Any] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        key, sep, raw = line.partition(':')
        if not sep or not KEY.fullmatch(key) or not raw.strip():
            raise ValueError('invalid flat frontmatter field: ' + line)
        if key in fields:
            raise ValueError('duplicate frontmatter field: ' + key)
        try:
            value = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            raise ValueError('field must use a JSON value: ' + key) from exc
        if isinstance(value, dict) or value is None:
            raise ValueError('unsupported frontmatter value: ' + key)
        fields[key] = value
    body = '\n'.join(lines[end + 1:]).strip()
    if not body:
        raise ValueError('prompt body is empty')
    return fields, body


def tool_set(value: Any) -> set[str]:
    if isinstance(value, str):
        return {v.strip() for v in value.split(',') if v.strip()}
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return set(value)
    return set()


def inside_file(root: Path, target: Path) -> bool:
    """A referenced file must exist and must not escape the package via symlinks."""
    try:
        resolved = target.resolve()
        return resolved.is_relative_to(root.resolve()) and resolved.is_file()
    except (OSError, RuntimeError):
        return False


def read_json(path: Path, report: Report) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report.check(False, str(path) + ': ' + str(exc))
        return None


def validate(root: Path, source_audit: bool = False) -> Report:
    root = root.resolve()
    out = Report()
    out.check(root.is_dir(), 'package root is not a directory')
    if not root.is_dir():
        return out
    for relative in sorted(REQUIRED):
        out.check(inside_file(root, root / relative), 'missing/escaping file: ' + relative)

    manifest = read_json(root / '.claude-plugin/plugin.json', out)
    out.check(isinstance(manifest, dict), 'manifest must be an object')
    if isinstance(manifest, dict):
        out.check(manifest.get('name') == 'speculative-generality', 'unexpected plugin name')
        out.check(bool(re.fullmatch(r'\d+\.\d+\.\d+', str(manifest.get('version', '')))),
                  'version must be a numeric semantic version')
        out.check(isinstance(manifest.get('description'), str) and bool(manifest['description'].strip()),
                  'manifest description missing')
        out.check(manifest.get('license') == 'MIT', 'unexpected license metadata')
        out.check(set(manifest) <= {'name', 'version', 'description', 'license', 'keywords'},
                  'unexpected manifest fields; inspect paths/side effects before extending')

    skill_files = sorted((root / 'skills').glob('*/SKILL.md'))
    agent_files = sorted((root / 'agents').glob('*.md'))
    out.counts['skills'] = len(skill_files)
    out.counts['agents'] = len(agent_files)
    out.check({p.parent.name for p in skill_files} == SKILLS, 'expected exactly three named skills')
    out.check({p.stem for p in agent_files} == AGENTS, 'expected exactly three named agents')
    for path in skill_files + agent_files:
        relative = str(path.relative_to(root))
        if not inside_file(root, path):
            out.check(False, 'escaping prompt: ' + relative)
            continue
        try:
            text = path.read_text(encoding='utf-8')
            data, body = frontmatter(text)
        except (OSError, UnicodeError, ValueError) as exc:
            out.check(False, relative + ': ' + str(exc))
            continue
        is_skill = path in skill_files
        name = path.parent.name if is_skill else path.stem
        out.check(data.get('name') == name, relative + ': frontmatter name mismatch')
        out.check(isinstance(data.get('description'), str) and bool(data['description'].strip()),
                  relative + ': description missing')
        out.check(len(text.splitlines()) < 500, relative + ': prompt exceeds 499 lines')
        refs = ROOT_REF.findall(body)
        out.check('rules/policy.md' in refs, relative + ': no explicit policy reference')
        for ref in refs:
            out.check(inside_file(root, root / ref), relative + ': broken/escaping root reference ' + ref)
        for role in ROLE_REF.findall(body):
            out.check(role in AGENTS, relative + ': unknown delegated role ' + role)
        if is_skill:
            out.check(data.get('disable-model-invocation') is True,
                      relative + ': must be manually invoked')
            out.check('$ARGUMENTS' in body, relative + ': missing argument placeholder')
            out.check('allowed-tools' not in data, relative + ': unexpected permission grant')
            out.check('context' not in data, relative + ': coordinator skill must not fork')
            allowed_fields = {'name', 'description', 'argument-hint',
                              'disable-model-invocation', 'disallowed-tools'}
            out.check(set(data) <= allowed_fields, relative + ': unsupported skill fields')
            if name in {'plan', 'review'}:
                out.check(tool_set(data.get('disallowed-tools')) == DENIED,
                          relative + ': missing read-only-turn tool denials')
        else:
            out.check(tool_set(data.get('tools')) == READ_TOOLS,
                      relative + ': advisory tools must be exactly Read, Grep, Glob')
            out.check(data.get('model') == 'inherit', relative + ': model should inherit')
            out.check(type(data.get('maxTurns')) is int and data['maxTurns'] == 12,
                      relative + ': expected maxTurns 12')
            out.check(set(data) <= {'name', 'description', 'tools', 'model', 'maxTurns'},
                      relative + ': unsupported/ignored agent fields')

    # Check authored Markdown links without any network requests.
    markdown = sorted(root.rglob('*.md'))
    out.counts['markdown_files'] = len(markdown)
    for path in markdown:
        if not inside_file(root, path):
            out.check(False, 'escaping Markdown file: ' + str(path))
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            out.check(False, str(path) + ': ' + str(exc))
            continue
        for raw in LOCAL_LINK.findall(text):
            parts = urlsplit(raw)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            target = path.parent / unquote(parts.path)
            out.check(inside_file(root, target), str(path.relative_to(root)) + ': broken local link ' + raw)

    if source_audit:
        cases_path = root / 'evals/cases.jsonl'
        try:
            lines = cases_path.read_text(encoding='utf-8').splitlines()
        except (OSError, UnicodeError) as exc:
            out.check(False, 'cannot read evaluation cases: ' + str(exc))
            lines = []
        case_ids: set[str] = set()
        modes: set[str] = set()
        count = 0
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            count += 1
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                out.check(False, f'case line {number}: invalid JSON: {exc}')
                continue
            if not isinstance(case, dict):
                out.check(False, f'case line {number}: must be an object')
                continue
            for field_name in ('id', 'title', 'mode', 'request', 'setup'):
                out.check(isinstance(case.get(field_name), str) and bool(case[field_name].strip()),
                          f'case line {number}: missing {field_name}')
            ident = case.get('id')
            if isinstance(ident, str):
                out.check(bool(re.fullmatch(r'SG\d{2}', ident)), f'case line {number}: malformed ID')
                out.check(ident not in case_ids, 'duplicate case ID: ' + ident)
                case_ids.add(ident)
            mode = case.get('mode')
            out.check(mode in ('PLAN', 'BUILD', 'REVIEW'), f'case line {number}: invalid mode')
            if isinstance(mode, str):
                modes.add(mode)
            for field_name in ('expected', 'forbidden', 'verification'):
                values = case.get(field_name)
                out.check(isinstance(values, list) and bool(values) and
                          all(isinstance(v, str) and bool(v.strip()) for v in values),
                          f'case line {number}: nonempty {field_name} list required')
        out.counts['behavioral_cases'] = count
        out.check(count == 12, 'expected twelve behavioral case records')
        out.check(modes == {'PLAN', 'BUILD', 'REVIEW'}, 'evaluation cases must cover all modes')

        sources = read_json(root / 'research/sources.json', out)
        if isinstance(sources, list):
            source_ids: set[str] = set()
            for source in sources:
                if not isinstance(source, dict):
                    out.check(False, 'source record must be an object')
                    continue
                ident = source.get('id')
                out.check(isinstance(ident, str) and ident not in source_ids, 'missing/duplicate source ID')
                if isinstance(ident, str):
                    source_ids.add(ident)
                out.check(bool(source.get('inspected')) and bool(source.get('access_note')),
                          str(ident) + ': source inspection/access information required')
                out.check(isinstance(source.get('url'), str) and source['url'].startswith('https://'),
                          str(ident) + ': source URL missing')
            out.counts['sources'] = len(sources)
        else:
            out.check(False, 'source audit must be a list')

    # Syntax compatibility only; not a Python 3.9 runtime execution claim.
    py_files = sorted(p for p in root.rglob('*.py') if '__pycache__' not in p.parts)
    out.counts['python_files'] = len(py_files)
    for path in py_files:
        if not inside_file(root, path):
            out.check(False, 'escaping Python file: ' + str(path))
            continue
        try:
            source = path.read_text(encoding='utf-8')
            ast.parse(source, filename=str(path), feature_version=(3, 9))
            out.check('from __future__ import annotations' in source,
                      str(path.relative_to(root)) + ': missing future annotations')
        except (OSError, UnicodeError, SyntaxError) as exc:
            out.check(False, str(path.relative_to(root)) + ': Python 3.9 syntax failure: ' + str(exc))
    return out


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--json', action='store_true', help='Emit a machine-readable package report')
    parser.add_argument('--source-audit', action='store_true',
                        help='Also require historical research and evaluation records in an original source checkout')
    args = parser.parse_args(argv)
    report = validate(args.root, source_audit=args.source_audit)
    if args.json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print(('PASS' if not report.errors else 'FAIL') + f': {report.checks} package checks')
        print(', '.join(f'{key}={value}' for key, value in report.counts.items()))
        for error in report.errors:
            print('ERROR: ' + error)
        print('Not tested here: native host loading or LLM behavior.')
    return 1 if report.errors else 0


if __name__ == '__main__':
    sys.exit(main())

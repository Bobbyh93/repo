#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

TOKEN = re.compile(r"{{\s*([a-zA-Z0-9_\.]+)\s*}}")

def get_path(data, dotted):
    cur = data
    for part in dotted.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur

def render_text(template, data, unresolved):
    def repl(match):
        key = match.group(1)
        value = get_path(data, key)
        if value is None:
            unresolved.append(key)
            return match.group(0)
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    return TOKEN.sub(repl, template)

def render_file(config_path, template_path, output_path):
    data = json.loads(Path(config_path).read_text(encoding='utf-8'))
    template = Path(template_path).read_text(encoding='utf-8')
    unresolved = []
    rendered = render_text(template, data, unresolved)
    Path(output_path).write_text(rendered, encoding='utf-8')
    print(json.dumps({"status": "rendered", "output_path": str(output_path), "unresolved": sorted(set(unresolved))}, indent=2))

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: render_prompt.py runtime_config.json template.md output.md', file=sys.stderr)
        sys.exit(2)
    render_file(sys.argv[1], sys.argv[2], sys.argv[3])

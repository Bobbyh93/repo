#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REQUIRED_TOP = ["runtime", "lesson", "sources", "taxonomy", "outputs", "layout", "qa"]
REQUIRED_RUNTIME = ["run_date_yyyymmdd", "package_id", "build_mode", "deployment_mode", "rebuild_scope", "output_root"]
VALID_BUILD_MODES = {"source_preflight", "blueprint", "full_production", "revision", "audio_video_handoff"}

MODE_REQUIRED = {
    "source_preflight": ["runtime.run_date_yyyymmdd", "runtime.package_id", "runtime.build_mode"],
    "blueprint": ["runtime.run_date_yyyymmdd", "runtime.package_id", "runtime.build_mode", "lesson.lesson_title"],
    "full_production": ["runtime.run_date_yyyymmdd", "runtime.package_id", "runtime.build_mode", "lesson.lesson_title", "outputs.target_outputs"],
    "revision": ["runtime.run_date_yyyymmdd", "runtime.package_id", "runtime.build_mode", "revision.change_request", "runtime.rebuild_scope"],
    "audio_video_handoff": ["runtime.run_date_yyyymmdd", "runtime.package_id", "runtime.build_mode", "lesson.lesson_title", "media.wpm_target"],
}

def get_path(data, dotted):
    cur = data
    for part in dotted.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur

def is_missing(value):
    return value is None or value == "" or value == [] or (isinstance(value, str) and value.strip().startswith("{{"))

def validate(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    errors = []
    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level object: {key}")
    runtime = data.get('runtime', {})
    for key in REQUIRED_RUNTIME:
        if is_missing(runtime.get(key)):
            errors.append(f"missing runtime.{key}")
    mode = runtime.get('build_mode')
    if mode not in VALID_BUILD_MODES:
        errors.append(f"invalid runtime.build_mode: {mode}")
    for dotted in MODE_REQUIRED.get(mode, []):
        if is_missing(get_path(data, dotted)):
            errors.append(f"missing required variable for {mode}: {dotted}")
    if errors:
        print(json.dumps({"status": "fail", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "pass", "checked_mode": mode}, indent=2))
    return 0

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: validate_runtime_config.py path/to/runtime_config.json', file=sys.stderr)
        sys.exit(2)
    sys.exit(validate(sys.argv[1]))

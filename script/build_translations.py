"""Build translations/en.json and pl.json from script/strings.json (resolves [%key:...%] references).

Usage: python script/build_translations.py <path to HA core homeassistant/strings.json>
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent / "custom_components/satel_integra"
strings = json.loads((Path(__file__).parent / "strings.json").read_text())
common = json.loads(Path(sys.argv[1]).read_text())
REF = re.compile(r"\[%key:([^%]+)%\]")


def lookup(path: str):
    parts = path.split("::")
    if parts[0] == "component":
        node = strings
        parts = parts[2:]
    else:
        node = common
    for part in parts:
        node = node[part]
    return resolve(node)


def resolve(value):
    if isinstance(value, dict):
        return {k: resolve(v) for k, v in value.items()}
    if isinstance(value, str):
        return REF.sub(lambda m: lookup(m.group(1)), value)
    return value


out = resolve(strings)
out.pop("common", None)
(ROOT / "translations").mkdir(exist_ok=True)
(ROOT / "translations/en.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n"
)
print("written", ROOT / "translations/en.json")

# Polish
sys.path.insert(0, str(Path(__file__).parent))
from pl_map import PL  # noqa: E402

missing = set()


def to_pl(value):
    if isinstance(value, dict):
        return {k: to_pl(v) for k, v in value.items()}
    if value not in PL:
        missing.add(value)
        return value
    return PL[value]


(ROOT / "translations/pl.json").write_text(
    json.dumps(to_pl(out), indent=2, ensure_ascii=False) + "\n"
)
print("missing pl:", missing or "none")

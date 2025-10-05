## Configuration schema (machine-readable)

Located at `docs/configuration/config_schema.json`, this JSON Schema is generated from `splurge_unittest_to_pytest.config_metadata` and is intended for editor autocompletion, validation, and tooling.

Usage
-----

- To validate a YAML or JSON configuration file, use any JSON Schema validator. For example, with `ajv` (npm) or `jsonschema` (Python).
- Editors such as VS Code will provide autocompletion and inline validation when you reference the schema in your workspace settings or via $schema pragmas.

Example (using Python's jsonschema):

```py
from pathlib import Path
import json
import yaml
from jsonschema import validate, ValidationError

schema = json.loads(Path("docs/configuration/config_schema.json").read_text())
config = yaml.safe_load(Path("my_config.yml").read_text())
try:
    validate(instance=config, schema=schema)
    print("Config is valid")
except ValidationError as exc:
    print("Config validation failed:", exc)
```

Notes
-----

- The schema encodes basic type information, defaults, enums (where specified), and numeric ranges when available. It does not (yet) encode inter-field constraints such as "Cannot be used with target_root" or "Cannot be used when backup_originals=False". These runtime constraints remain enforced in `config_validation.py`.
- If you need those cross-field constraints in machine-checkable form, we can extend the generator to emit `allOf`/`if/then/else` blocks in the JSON Schema.

Would you like me to add an automated generator (a small CLI command) that re-emits this schema from `config_metadata.py` so the schema stays in sync as metadata changes?

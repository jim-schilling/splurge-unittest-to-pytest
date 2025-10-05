# Programmatic API

This module describes the main programmatic entrypoints and their usage.

## migrate(source_files, config=None, event_bus=None)

Signature:

- `migrate(source_files: Iterable[str] | str, config: MigrationConfig | None = None, event_bus: EventBus | None = None) -> Result[list[str]]`

Description:

- Main programmatic entry point for converting one or more unittest files to pytest.
- Accepts a single path string or an iterable of paths.
- Optional `MigrationConfig` controls behavior; when omitted a default config is used.
- Optional `EventBus` can be provided to subscribe to progress events.
- Returns a `Result` object. On success, `Result.data` contains a list of written target paths. When running a dry-run, `Result.metadata` may contain a `generated_code` mapping of target paths to generated source.

Example:

```python
from splurge_unittest_to_pytest.main import migrate
from splurge_unittest_to_pytest.context import MigrationConfig

config = MigrationConfig()
config.dry_run = True

result = migrate(["tests/test_example.py"], config=config)
if result.is_success():
    print("Would write:", result.data)
    gen = result.metadata.get("generated_code", {}) if result.metadata else {}
    for target, code in gen.items():
        print(f"--- {target} ---")
        print(code)
else:
    print("Migration failed:", result.error)
```

Notes:

- The `migrate` function defers to `MigrationOrchestrator` for per-file migration. Tests and other integrations may monkeypatch `MigrationOrchestrator` or the `migrate_file` method for fine-grained control.
- The `Result` class provides `Result.success(data, metadata=None)` and `Result.failure(error)` convenience constructors.

Event hooks and EventBus

- The optional `EventBus` can be used to listen for progress events produced by the migration pipeline. Provide your own `EventBus` implementation or use the library's default `create_event_bus()` helper when available.

EventBus example

```python
from splurge_unittest_to_pytest.events import create_event_bus, Event
from splurge_unittest_to_pytest.main import migrate

bus = create_event_bus()

def on_progress(ev: Event) -> None:
    # Event has a `name` and a `payload` dict with structured data.
    if ev.name == "file.migrate.started":
        print(f"Starting: {ev.payload['source']}")
    elif ev.name == "file.migrate.completed":
        print(f"Finished: {ev.payload['target']} (wrote={ev.payload.get('wrote', False)})")

bus.subscribe(on_progress)

result = migrate(["tests/test_example.py"], config=None, event_bus=bus)
if result.is_success():
    print("Migration completed for:", result.data)
```

Notes:
- Events are designed for lightweight monitoring and logging. Event names are namespaced (e.g., `file.migrate.started`, `file.migrate.completed`, `migration.summary`).
- The `EventBus` implementation provided by this package is thread-safe and supports multiple subscribers.


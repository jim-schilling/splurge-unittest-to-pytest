```markdown
Spec: assertion_rewriter Steps

Purpose
-------
Define the expected behavior, inputs/outputs, and test harness for the `assertion_rewriter` Task migration to Steps.

Data shapes
-----------
- ContextDelta.values is a mapping of string -> JSON-serializable values used between Steps. Keys used in this spec:
  - `module_cst` : the module-level CST node (or a serializable representation)
  - `assertions_parsed` : list[dict] internal assertion descriptors
  - `assertions_transformed` : list[CST] fragments ready for emission
  - `emitted_nodes` : list[CST] nodes appended/replaced in module

Step contracts (detailed)
-------------------------
Each Step implements:

class ExampleStep(Step):
    name = "example"
    id = "example:1"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        """Return StepResult with delta, diagnostics, errors, skipped."""

Error handling
--------------
- Steps must prefer returning errors via StepResult.errors over raising where possible. Raising exceptions should be reserved for unexpected runtime failures.
- The runner will treat non-empty StepResult.errors as stopping errors and publish StepErrored/TaskErrored.

Test cases
----------
1) ParseAssertionsStep - happy path
   - Input: module with a few assert statements
   - Expect: `assertions_parsed` contains parsed descriptors; no errors; diagnostics empty

2) ParseAssertionsStep - returns errors
   - Input: malformed assertion node that helper detects
   - Expect: StepResult.errors non-empty; runner stops; no `assertions_transformed` present

3) TransformAssertionsStep - happy path
   - Input: `assertions_parsed` produced above
   - Expect: `assertions_transformed` present; no errors

4) EmitAssertionsStep - happy path
   - Input: `assertions_transformed`
   - Expect: `emitted_nodes` present and module_cst updated in working context

5) Runner integration parity
   - Run Task original implementation to get baseline converted module
   - Run Task via `run_steps` executing the 3 Steps and compare outputs (string AST/CST) for equality

Test harness
------------
- Use existing test data in `tests/data/` and `tests/unit/` test helpers.
- Use `tmp_path` fixtures for temporary files.

Performance & safety
--------------------
- Keep transformations memory-friendly: operate on lists of nodes rather than duplicating entire module when possible.

Acceptance criteria
-------------------
- All step unit tests pass.
- Runner integration parity test passes for sampled files.
- Full suite passes: ruff, mypy, pytest -n 9.

``` 

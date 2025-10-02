# Plan: Multi-pass Transformer Architecture (2025-10-01)

Purpose
-------
This document records a concrete design and implementation plan for adding a deterministic, traceable multi-pass transformation pipeline to the splurge-unittest-to-pytest project. The new pipeline will collect evidence across module/class/function scopes, allow proposals to bubble up and be revised, and then apply canonical transformations deterministically.

High-level goals
-----------------
- Make translation decisions explicit, testable, and debuggable.
- Avoid unsafe, context-free rewrites; prefer conservative defaults with opt-in lifting to parametrize.
- Preserve semantics where the original code mutates accumulators or depends on loop ordering.
- Eliminate ad-hoc global string replacements by favoring AST-level rewrites and controlled fallbacks.

Passes and responsibilities
---------------------------
We propose a 5-pass pipeline.

Pass-0: Normalization (optional)
- Run small syntactic normalizations (e.g., collapse parentheses around a single With item) to make downstream pattern matching simpler.
- Guarantee a consistent CST shape for complex constructs (parenthesized With items, combined-withs) so scanners can rely on stable structure.

Pass-1: Module scanner
- Walk the Module-level AST and collect top-level facts:
  - Top-level assignments (e.g., `scenarios = []`), module-level fixtures, and imports.
  - Look for file-level patterns (e.g., DATA constants, names referencing `test_cases` files).
- Record module-level hints in the DecisionModel (see below).

Pass-2: Class scanner
- Walk ClassDef nodes and collect per-class facts:
  - Presence of `setUp`/`tearDown`, class-level fixtures, `@classmethod setUpClass` patterns.
  - Accumulator fields on `self` or class attributes used as test data.
- Aggregate and store per-class hints and also allow storing method-level proposals.

Pass-3: Function scanner
- Walk each FunctionDef (test methods and helper functions) and detect rewrite opportunities and risks:
  - For-loops that wrap `self.subTest(...)` where the loop iterable is either a literal list/tuple or a named reference to a variable assigned earlier.
  - Detect accumulator patterns (`scenarios = []` followed by `.append`) and mark them as "accumulator-mutated" to avoid lifting into parametrize.
  - Detect combined `with` items like `with (self.assertRaises(...) as exc, self.assertLogs(...) as log):` and record the alias names (`exc`, `log`) and their usage (`.exception`, `.records`, `.output`, `.getMessage()`) so downstream transforms prefer `caplog.records` vs `caplog.messages` conservatively.
- Emit a FunctionProposal object describing the recommended strategy for each function: parametrize, subtests-fixture, keep-loop, and associated metadata (aliases, mutated names, evidence lines).

Pass-4: Bubbler / proposal reconciler
- Aggregate FunctionProposals into ClassProposals and ModuleProposals.
- Rule-set for bubbling examples:
  - If all functions in a class propose `parametrize` for the same loop-variable and the module has no accumulator mutation of that name, mark class-level parametrize allowed.
  - If any function proposes `keep-loop` due to mutation, do not lift to class-level parametrize; instead prefer `subtests` fixture for functions that need it.
- The bubbler may revise function proposals when conflicts appear (e.g., require subtests when module-level fixtures collide).

Pass-5: Finalizer / executor
- Walk functions and apply canonical AST rewrites based on the final, bubbled decisions using existing helper modules:
  - `parametrize_helper` to convert for+subTest loops into `@pytest.mark.parametrize`.
  - `subtest_transformer` to convert `self.subTest` into `subtests.test` when preserving the loop.
  - `assert_transformer` and caplog rewrite utilities to rewrite `assertLogs`/`caplog` aliases to `caplog.records`/`caplog.messages` conservatively; DO NOT synthesize `_caplog`.
- Also inject required fixtures (`subtests`, `caplog` if used, etc.) at function signature level.

Decision model: data structures and contracts
--------------------------------------------
We'll add a small typed module `splurge_unittest_to_pytest/decision_model.py` with dataclasses:
- DecisionModel
  - module_proposals: dict[str, ModuleProposal]
  - class_proposals: dict[str, ClassProposal]
  - function_proposals: dict[str, FunctionProposal]

- FunctionProposal
  - function_name: str
  - recommended_strategy: Literal['parametrize','subtests','keep-loop']
  - loop_var_name?: str
  - iterable_origin: Literal['literal','name','call']
  - accumulator_mutated: bool
  - caplog_aliases: List[CaplogAliasMetadata]
  - evidence: List[str] (line snippets or node paths)

- ClassProposal and ModuleProposal aggregate function proposals and store summary decisions.

Contracts
- Inputs: a Module CST; outputs: a DecisionModel and then a transformed CST.
- Error modes: if scanners encounter unknown/malformed nodes, they should record a conservative "keep-loop" recommendation and add an evidence note but not crash.
- Success: functions with unambiguous literal iterables converted to parametrize; accumulator-mutated sequences preserved; caplog alias rewrites applied conservatively.

Examples and canonical rules
----------------------------
- Lift to @pytest.mark.parametrize when:
  - The loop iterable is a literal list/tuple or a simple name referencing a prior assignment that's not mutated before the loop.
  - There is no dependency on surrounding mutable state or ordering that would change semantics.

- Keep-loop and convert to `subtests.test` when:
  - The iterable originates from an accumulator that is appended/augmented prior to the loop.
  - The assignment to the iterable variable is mutated or it is a global that is mutated between tests.

- Caplog/assertLogs alias mapping rules (conservative):
  - When assertLogs is used as `with self.assertLogs(logger, level=logging.ERROR) as log_ctx:` and later `log_ctx.records` or attribute access is used, map the alias to `caplog.records` and inject `caplog` fixture.
  - When only membership or message comparison uses are present (e.g., `"something" in log_ctx.output`), map to `caplog.messages`.
  - Never synthesize a `_caplog` alias.

Testing and verification
------------------------
- Add unit tests for scanners and the DecisionModel behavior: e.g., a test module that includes
  - A literal for-loop -> expect FunctionProposal recommending `parametrize`.
  - An accumulator-based pattern -> expect `keep-loop` and `subtests` recommendation.
  - Combined-with with assertRaises/assertLogs -> expect CaplogAliasMetadata recorded with correct alias names and recommendations.
- Run the full test-suite after each major change. Focused test runs are OK while iterating but ensure a final full-run passes.

Implementation Plan (phases)
----------------------------
Phase A (scaffold) - 1 day
- Add `decision_model.py` with dataclasses and basic serialization (repr/str) for debugging.
- Add a simple function-scanner that uses existing `parametrize_helper` detection logic to emit FunctionProposals for test functions.
- Wire the scanner into `unittest_transformer.py` to run pass-3 and store decisions in a `DecisionModel` instance attached to the transform session.
- Add unit tests for the scanner.

Phase B (bubbler + finalizer skeleton) - 2 days
- Implement the bubbler that aggregates function proposals into class/module proposals and applies simple reconciliation rules.
- Implement a finalizer skeleton that reads decisions and calls into existing transformers (without changing the code) — the finalizer should be a no-op placeholder that logs planned changes.
- Add tests that assert the bubbler's aggregated decisions for a few synthetic modules.

Phase C (executor) - 3 days
- Implement final AST rewrite steps using `parametrize_helper`, `subtest_transformer`, and `assert_transformer` to actually mutate the code.
- Add fixture injection and final canonicalization rules.
- Run full test-suite and fix regressions.

Phase D (polish + docs) - 1 day
- Add documentation (this file) to `docs/plans/`.
- Update README with notes about the multi-pass pipeline and how to add new rules.
- Clean up logging and add helpful debug dump outputs for DecisionModel for developers.

Rollback and safety
-------------------
- Each change will be done in a feature branch and committed with clear messages.
- Tests must be added for any behavior change and run before merging.
- If a produced change is unsafe, fall back to conservative "keep-loop" behavior.

Open questions
--------------
- Do we want pass-0 normalization as a fixed pre-step or an on-demand helper? Recommendation: make it an optional utility invoked by the pipeline.
- How verbose should the DecisionModel debug dumps be by default? Recommendation: medium verbosity, with a --debug flag for full dumps.


Appendix: Minimal API sketch (python)
-------------------------------------

from dataclasses import dataclass
from typing import List, Literal, Optional
import libcst as cst

@dataclass
class CaplogAliasMetadata:
    alias_name: str
    used_as_records: bool
    used_as_messages: bool
    locations: List[str]

@dataclass
class FunctionProposal:
    function_name: str
    recommended_strategy: Literal['parametrize','subtests','keep-loop']
    loop_var_name: Optional[str] = None
    iterable_origin: Optional[Literal['literal','name','call']] = None
    accumulator_mutated: bool = False
    caplog_aliases: List[CaplogAliasMetadata] = None
    evidence: List[str] = None

# DecisionModel: hold proposals and helper methods to summarize

class DecisionModel:
    ...


Notes
-----
- This plan intentionally prioritizes safety over aggressive lifting. The goal is to reduce false positives and produce transformations that preserve test semantics.
- The initial scaffold will be small and test-driven so we can iterate quickly.


Created: 2025-10-01
Author: automated-assistant (pair-programmer)

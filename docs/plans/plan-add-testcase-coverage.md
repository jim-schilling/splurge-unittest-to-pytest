# Plan: Add TestCase API Coverage

This supplemental plan documents the tasks required to add support for a broad set of TestCase instance APIs and maps them to the IR and pytest constructs.

Requested APIs to support:

- TestCase.skipTest()
- TestCase.assertLogs()
- TestCase.assertNoLogs()
- TestCase.id()
- TestCase.typeEqualityFunc()
- TestCase.assertMultiLineEqual()
- TestCase.assertSequenceEqual()
- TestCase.fail()
- TestCase.shortDescription()
- TestCase.addCleanup()
- TestCase.doCleanups()
- TestCase.addClassCleanup()
- TestCase.doClassCleanups()
- TestCase.enterContext()
- TestCase.enterClassContext()
- TestCase.subTest()

Implementation strategy (summary):

1) Design & Contract - document mapping and edge cases.
2) IR & Analyzer - extend `ir.py` and `UnittestPatternAnalyzer` to capture uses.
3) CST Transformer - add visitor transforms to convert patterns or annotate IR.
4) IR-to-pytest Generator - emit safe pytest equivalents or conservative fallbacks.
5) Tests & Docs - add unit and integration tests and update docs.

Acceptance criteria:
- Each API is recognized in IR or has a documented fallback.
- Automatic mappings preserve semantics where possible.
- Tests validate mapping behavior and edge cases.

Estimated timeline: 2-3 weeks (iterative, can be parallelized across tasks).
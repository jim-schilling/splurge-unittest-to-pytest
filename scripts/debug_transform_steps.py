import libcst as cst
from libcst.metadata import MetadataWrapper

from splurge_unittest_to_pytest.transformers.assert_transformer import transform_with_items
from splurge_unittest_to_pytest.transformers.transformer_helper import ReplacementApplier
from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

path = "tests/data/given_and_expected/unittest_given_09.txt"
code = open(path, encoding="utf-8").read()
module = cst.parse_module(code)
wrapper = MetadataWrapper(module)
transf = UnittestToPytestCstTransformer()
# Run main transformer
transformed1 = wrapper.visit(transf)
print("--- after main transformer ---")
print(transformed1.code)
# apply replacement registry if any
if transf.replacement_registry.replacements:
    applied = MetadataWrapper(transformed1).visit(ReplacementApplier(transf.replacement_registry))
    print("--- after replacement applier ---")
    print(applied.code)
else:
    applied = transformed1
    print("--- no replacements recorded ---")
class RemainingWithRewriter(cst.CSTTransformer):
    def leave_With(self, original: cst.With, updated: cst.With) -> cst.With:
        try:
            new_with, alias, changed = transform_with_items(updated)
            return new_with
        except Exception:
            return updated


parsed = cst.parse_module(applied.code)
final = parsed.visit(RemainingWithRewriter())
print("--- after RemainingWithRewriter ---")
print(final.code)

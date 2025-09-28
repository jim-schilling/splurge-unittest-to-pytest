from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

p = "tests/data/given_and_expected/unittest_given_21.txt"
with open(p, encoding="utf-8") as f:
    src = f.read()
tr = UnittestToPytestCstTransformer()
out = tr.transform_code(src)
print("--- TRANSFORMED START ---")
print(out)
print("--- TRANSFORMED END ---")


## Running just one test

```
python -m unittest tests.test_pop.TestPop3.test_CAPA
```

## Patch for enable logging in test

Patch generated using below
```
git diff --patch -U1 tests >> ./DEVNOTES.md
```

```bash
git apply - <<PATCH
diff --git a/tests/test_pop.py b/tests/test_pop.py
index 55c1a91..a825665 100644
--- a/tests/test_pop.py
+++ b/tests/test_pop.py
@@ -55,3 +55,3 @@ def setUpModule() -> None:
     global MAILS_PATH
-    logging.basicConfig(level=logging.CRITICAL)
+    logging.basicConfig(level=logging.DEBUG)
     td = tempfile.TemporaryDirectory(prefix="m41.pop.")
PATCH
```

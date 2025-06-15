Notes for developers

## Running just one test

```
python -m unittest tests.test_pop.TestPop3.test_CAPA
python -m unittest tests.test_smtp.TestSMTP
```

## Patch for enable logging in test

Patch generated using below

```
git diff --patch -U1 tests >> ./DEVNOTES.md
```

Apply with below. Disables smtp test mail dir cleanup.
```
ls -ltd /tmp/m41*
git checkout tests
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
diff --git a/tests/test_smtp.py b/tests/test_smtp.py
index 0554d4c..52d147b 100644
--- a/tests/test_smtp.py
+++ b/tests/test_smtp.py
@@ -18,5 +18,5 @@ def setUpModule() -> None:
     global MAILS_PATH
-    logging.basicConfig(level=logging.CRITICAL)
+    logging.basicConfig(level=logging.DEBUG)
     td = tempfile.TemporaryDirectory(prefix="m41.smtp.")
-    unittest.addModuleCleanup(td.cleanup)
+    # unittest.addModuleCleanup(td.cleanup)
     MAILS_PATH = Path(td.name)
PATCH
```

## pylint

```
pylint mail4one/*py > /tmp/errs
vim +"cfile /tmp/errs"
```

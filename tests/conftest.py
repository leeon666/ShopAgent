import os
import tempfile

os.environ.setdefault("SHOP_DB_PATH", os.path.join(tempfile.mkdtemp(), "test.db"))

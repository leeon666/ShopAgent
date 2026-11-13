"""应用配置：数据库连接等。"""
import os


def _default_database_url() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return f"sqlite:///{os.path.join(data_dir, 'shop.db').replace(os.sep, '/')}"


DATABASE_URL = os.environ.get("DATABASE_URL", _default_database_url())

SECRET_KEY = os.environ.get("SHOP_SECRET_KEY", "ecommerce-shop-dev-secret-key-change-me")
TOKEN_TTL_HOURS = int(os.environ.get("SHOP_TOKEN_TTL_HOURS", "24"))

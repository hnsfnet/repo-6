from app.stores.base_store import MessageStore
from app.stores.in_memory_store import InMemoryStore
from app.core.config import get_config


def create_store() -> MessageStore:
    cfg = get_config()
    if cfg.message_store_type == "in_memory":
        return InMemoryStore()
    return InMemoryStore()


message_store: MessageStore = create_store()

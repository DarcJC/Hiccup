from hiccup.db.user import *
from hiccup.db.server import *
from hiccup.db.base import Base, DATABASE_URL, AsyncSessionLocal, get_db


models = [
    # user
    AnonymousIdentify,
    ClassicIdentify,
    AuthToken,
    # server
    VirtualServer,
    Channel,
]


__all__ = ['Base', 'DATABASE_URL', 'AsyncSessionLocal', 'get_db', 'models']

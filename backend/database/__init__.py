from .database import engine, SessionLocal, Base, get_db
from .models import CommandHistory, Reminder, AppRegistry, AppSetting

Base.metadata.create_all(bind=engine)

__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "CommandHistory",
    "Reminder",
    "AppRegistry",
    "AppSetting",
]

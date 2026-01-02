from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Import all models here to register them with SQLAlchemy
# This must happen after Base is defined
from app.models import enums, organization, user, agent, chat, license  # noqa: F401, E402

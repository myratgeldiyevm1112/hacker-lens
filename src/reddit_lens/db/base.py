from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Common declarative base for all ORM models. Every model inherits
    from this class so SQLAlchemy collects their metadata in one
    place, which Alembic later reads to autogenerate migrations.
    """

    pass
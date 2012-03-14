""" Common metadata modules
"""

import threading
import warnings

from sqlalchemy import text
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship as Relationship
from sqlalchemy.schema import Column
from sqlalchemy.schema import CheckConstraint
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.schema import Index
from sqlalchemy.schema import ForeignKeyConstraint
from sqlalchemy.types import Enum
from sqlalchemy.types import DateTime
from sqlalchemy.types import String
from sqlalchemy.types import Unicode

from sqlalchemy.ext.declarative import has_inherited_table
from sqlalchemy.types import Integer

from occams.datastore.model.model import Model


NOW = text('CURRENT_TIMESTAMP')

registry = threading.local()
registry.user = None


def setActiveUser(user):
    if user.id is None:
        warnings.warn(
            'Setting active user that does not have an ID number yet. '
            'Possibly this method was called before flushing the user to the '
            'database.'
            )
    registry.user = user


def getActiveUser():
    return registry.user


def getActiveUserId():
    return registry.user.id


def clearActiveUser():
    registry.user = None


class AutoNamed(object):
    """
    Generates the SQL table name from the class name.
    """

    @declared_attr
    def __tablename__(cls):
        if has_inherited_table(cls) and AutoNamed not in cls.__bases__:
            return None
        return cls.__name__.lower()


class Referenceable(object):
    """
    Adds primary key id columns to tables.
    """

    id = Column(Integer, primary_key=True)


class Describeable(object):
    """
    Adds standard content properties to tables.
    """

    name = Column(String, nullable=False)

    title = Column(Unicode, nullable=False)

    description = Column(Unicode)


class User(Model, AutoNamed, Referenceable):

    email = Column(String, nullable=False)

    fullname = Column(Unicode)

    create_date = Column(DateTime, nullable=False, server_default=NOW)

    modify_date = Column(DateTime, nullable=False, server_default=NOW, onupdate=NOW)

    __table_args__ = (
        UniqueConstraint('email'),
        CheckConstraint('create_date <= modify_date', 'ck_user_valid_timeline'),
        )


class Log(Model, AutoNamed, Referenceable):

    user_id = Column(Integer, nullable=False)

    user = Relationship('User')

    action = Column(
        Enum('add', 'update', 'delete', name='log_action'),
        nullable=False
        )

    previous = Column(Unicode)

    current = Column(Unicode)

    log_date = Column(DateTime, nullable=False, server_default=NOW)

    __table_args__ = (
        ForeignKeyConstraint(
            columns=['user_id'],
            refcolumns=['user.id'],
            name='fk_%s_user_id' % 'log',
            ondelete='RESTRICT'
            ),
        )


def buildModifiableConstraints(cls):
    """
    Returns constrains for modifiable columns, tailored for the specified class

    There doesn't seem to be a good way to put this as a ``declared_attr`` of
    ``Modifiable``, dude the difficulty of using ``super`` on ``property``
    decorators. This, though, is a better alternative as opposed to
    copying and pasting the constraints to each class.
    """
    return (
        ForeignKeyConstraint(
            columns=['create_user_id'],
            refcolumns=['user.id'],
            name='fk_%s_create_user_id' % cls.__tablename__,
            ondelete='RESTRICT'
            ),
        ForeignKeyConstraint(
            columns=['modify_user_id'],
            refcolumns=['user.id'],
            name='fk_%s_modify_user_id' % cls.__tablename__,
            ondelete='RESTRICT'
            ),
        CheckConstraint(
            'create_date <= modify_date',
            'ck_%s_valid_timeline' % cls.__tablename__
            ),
        Index('ix_%s_create_user_id' % cls.__tablename__, 'create_user_id'),
        Index('ix_%s_modify_user_id' % cls.__tablename__, 'modify_user_id'),
        )


class Modifiable(object):
    """
    Adds user edit modification meta data for lifecycle tracking.
    """

    @declared_attr
    def create_date(cls):
        return Column(DateTime, nullable=False, server_default=NOW)

    @declared_attr
    def create_user_id(cls):
        return Column(Integer, nullable=False, default=getActiveUserId)

    @declared_attr
    def create_user(cls):
        return Relationship('User',
            primaryjoin='%s.create_user_id == User.id' % cls.__name__)

    @declared_attr
    def modify_date(cls):
        return Column(DateTime, nullable=False, server_default=NOW, onupdate=NOW)

    @declared_attr
    def modify_user_id(cls):
        return Column(Integer, nullable=False, default=getActiveUserId)

    @declared_attr
    def modify_user(cls):
        return Relationship('User',
            primaryjoin='%s.modify_user_id == User.id' % cls.__name__)

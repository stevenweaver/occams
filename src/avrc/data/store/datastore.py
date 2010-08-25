"""
Datastore implementation module as supporting utilities.
"""
from collections import deque as queue
from time import time as currenttime
from datetime import datetime, date, time
import logging

from zope.component import getSiteManager
from zope.component import provideUtility
from zope.component import getUtility
from zope.component import queryUtility
from zope.component import adapter
from zope.component.factory import Factory
from zope.interface import implements
from zope.interface import providedBy
from zope.interface import directlyProvides
from zope.i18nmessageid import MessageFactory
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent
from zope.lifecycleevent import IObjectCreatedEvent
from zope.lifecycleevent import IObjectRemovedEvent
import zope.schema
from zope.schema.interfaces import IVocabulary
from zope.schema.fieldproperty import FieldProperty

import sqlalchemy as sa
from sqlalchemy import orm

from avrc.data.store import model
from avrc.data.store import interfaces

_ = MessageFactory(__name__)

log = logging.getLogger(__name__)

_ECHO_ENABLED = False

_DS_FMT = u"<Datastore '%s'>"

def session_name_format(datastore):
    """
    Helper method to format a session name corresponding to the data store.

    Arguments:
        datastore: (object) an object implementing IDatastore
    Returns:
        A string to use as the session utility name.
    """
    return "%s:session" % str(datastore)

def named_session(datastore):
    """
    Evaluates the session being used by the given data store.

    Arguments:
        datastore: (object) an object implementing IDatastore
    Returns:
        A sqlalchemy Session factory.
    """

    return datastore.getSession()

def setup_types(datastore):
    """
    Helper method to setup up built-in supported types.

    Arguments:
        datastore: (object) an object implementing IDatastore
    Returns:
        N/A
    """
    rslt = []
    Session = named_session(datastore)
    session = Session()
    types = getUtility(zope.schema.interfaces.IVocabulary,
                       "avrc.data.store.Types")

    for t in list(types):
        rslt.append(model.Type(
            title=unicode(t.token),
            description=unicode(getattr(t.value, "__doc__", None)),
            ))

    session.add_all(rslt)
    session.commit()

@adapter(interfaces.IDatastore, IObjectCreatedEvent)
def handleDatastoreCreated(datastore, event):
    """
    Triggered when a new DataStore instance is added to a container (i.e.
    when it is added to a site. Essentially, it setups up the database
    back-end.

    Arguments:
        datastore: (object) the newly created object implementing IDatastore
        event: (object) the event object
    Returns:
        N/A
    """
    Session = SessionFactory(bind=sa.create_engine(datastore.dsn,
                                                   echo=_ECHO_ENABLED))

    sm = getSiteManager(datastore)
    sm.registerUtility(Session,
                       interfaces.ISessionFactory,
                       session_name_format(datastore))

    model.setup(Session.bind)
    setup_types(datastore)


@adapter(interfaces.IDatastore, IObjectRemovedEvent)
def handleDatastoreRemoved(datastore, event):
    """
    Triggered when a new DataStore instance is removed from a container

    Arguments:
        datastore: (object) the removed object implementing IDatastore
        event: (object) the event object
    Returns:
        N/A
    """
    # TODO do ti for the site
    provideUtility(None,
                   interfaces.ISessionFactory,
                   session_name_format(datastore))

from persistent import Persistent

class SessionFactory(Persistent):
    implements(interfaces.ISessionFactory)

    __doc__ = interfaces.ISessionFactory.__doc__

    __name__ = None

    __parent__ = None

    def __init__(self,
                 autocommit=False,
                 autoflush=True,
                 twophase=False,
                 bind=None,
                 binds=None):
        """
        Our ISessionFactory implementation takes an extra parameter which
        will be the database bindings.

        TODO: (mmartinez) Perhaps make an adapter to extend the functionality
            of z3c.saconfig?
        """
        self.autocommit = autocommit
        self.autoflush = autoflush
        self.twophase = twophase
        self.binds = binds
        self.bind = bind
        super(Persistent, self).__init__()

    def __call__(self):
        Session  = orm.scoped_session(orm.sessionmaker(
            autocommit=self.autocommit,
            autoflush=self.autoflush,
            twophase=self.twophase
            ))

        Session.configure(bind=self.bind, binds=self.binds)
        if Session is None:
            raise Exception('wtf??')
        return Session

    __call__.__doc__ = interfaces.ISessionFactory["__call__"].__doc__

class Instance(object):
    implements(interfaces.IInstance)

    __doc__ = interfaces.IInstance.__doc__

    __id__ = None

    __schema__ = None

    title = None

    description = None

    def __str__(self):
        return "<%s, implements %s>" % (self.title, self.__schema__)

class Datastore(object):
    implements(interfaces.IDatastore)

    __doc__ = interfaces.IDatastore.__doc__

    __name__ = None

    __parent__ = None

    title = FieldProperty(interfaces.IDatastore["title"])

    dsn = FieldProperty(interfaces.IDatastore["dsn"])

    def __init__(self, title, dsn):
        """
        Instantiates the data store implementation. Also notifies listeners
        that this object has been created.

        Arguments:
            title: (str) the name of this data store instance
            dsn: (str) the URI to the data base
        """
        self.title = title
        self.dsn = dsn

        notify(ObjectCreatedEvent(self))

    def __str__(self):
        """
        String representation of this instance
        """
        return _DS_FMT % self.title

    def getSession(self):
        sm = getSiteManager(self)
        session = sm.queryUtility(interfaces.ISessionFactory, session_name_format(self))
        if session is not None:
            return sm.queryUtility(interfaces.ISessionFactory, session_name_format(self))
        else:
            Session = SessionFactory(bind=sa.create_engine(self.dsn,
                                                   echo=_ECHO_ENABLED))

            sm.registerUtility(Session,
                       interfaces.ISessionFactory,
                       session_name_format(self))
        return  sm.queryUtility(interfaces.ISessionFactory, session_name_format(self))

    @property
    def schemata(self):
        """A schema manager utility"""
        return interfaces.ISchemaManager(self)

    @property
    def domains(self):
        """A protocol manager utility"""
        return interfaces.IDomainManager(self)

    @property
    def subjects(self):
        """A protocol manager utility"""
        return interfaces.ISubjectManager(self)

    @property
    def protocols(self):
        """A protocol manager utility"""
        return interfaces.IProtocolManager(self)

    @property
    def enrollments(self):
        """A protocol manager utility"""
        return interfaces.IEnrollmentManager(self)

    @property
    def visits(self):
        """A protocol manager utility"""
        return interfaces.IVisitManager(self)

    def keys(self):
        # This method will remain unimplemented as it doesn't really make sense
        # to return every single key in the data store.
        pass

    keys.__doc__ = interfaces.IDatastore["keys"].__doc__

    def has(self, key):
        # we're going to use the object as the key (or it's 'name')
        Session = named_session(self)
        session = Session()

        if isinstance(key, (str, unicode)):
            key = str(key)
        elif interfaces.IInstance.providedBy(key):
            key = key.__id__
        else:
            raise Exception("The object specified cannot be evaluated into "
                            "a object to search for")

        instance_rslt = session.query(model.Instance)\
                        .filter_by(id=key)\
                        .first()

        return instance_rslt is not None

    has.__doc__ = interfaces.IDatastore["has"].__doc__

    def get(self, key):
        # Since the object doesn't have any dependencies on it's data, we're
        # just going to do another Breadth-first traversal
        #
        # TODO: (mmartinez) get by title as well, currently only works
        #    by id....
        #
        # TODO: (mmartinez) objects come back without their interfaces currently
        #

        # we're going to use the object as the key (or it's 'name')
        types = getUtility(IVocabulary, "avrc.data.store.Types")
        Session = named_session(self)
        session = Session()

        if isinstance(key, (str, unicode)):
            key = str(key)
        elif interfaces.IInstance.providedBy(key):
            key = key.__id__
        else:
            raise Exception("The object specified cannot be evaluated into "
                            "a object to search for")

        instance_rslt = session.query(model.Instance)\
                        .filter_by(id=key)\
                        .first()

        if instance_rslt is None:
            return None

        instance_obj = Instance()
        setattr(instance_obj, "__id__", instance_rslt.id)

        # (parent object, parent db entry, prop name, value)
        to_visit = queue([(instance_obj, instance_rslt, None, None)])

        while len(to_visit) > 0:
            (parent_obj, instance_rslt, attr_name, value) = to_visit.popleft()

            for attribute_rslt in instance_rslt.schema.attributes:

                type_name = attribute_rslt.field.type.title

                if type_name in (u"binary",):
                    Model = model.Binary
                elif type_name in (u"date", u"time", u"datetime"):
                    Model = model.Datetime
                elif type_name in (u"integer",):
                    Model = model.Integer
                elif type_name in (u"real",):
                    Model = model.Real
                elif type_name in (u"object",):
                    Model = model.Object
                elif type_name in (u"text", u"string"):
                    Model = model.String
                elif type_name in (u"selection"):
                    Model = model.Selection
                else:
                    raise Exception("Type '%s' unsupported."  % type_name)

                value_q = session.query(Model)\
                                .filter_by(instance=instance_rslt)\
                                .filter_by(attribute=attribute_rslt)\

                if type_name in (u"object",):
                    raise Exception("Using nested objects, not supported yet...")
                    instance_obj = Instance()
                    # TOD fix this...
                    setattr(instance_obj, "__id__", None)
                    setattr(parent_obj, str(attribute_rslt.name), instance_obj)
                    #to_visit.append((object_rslt.value, instance_obj, None, None,))
                else:
                    if attribute_rslt.field.is_list:
                        value = [v.value for v in value_q.all()]
                    else:
                        value = value_q.first()

                    setattr(parent_obj, str(attribute_rslt.name), value)

        return instance_obj

    get.__doc__ = interfaces.IDatastore["get"].__doc__

    def put(self, target):
        types = getUtility(IVocabulary, "avrc.data.store.Types")
        Session = named_session(self)
        session = Session()

        # (parent object, corresponding db entry, prop name, raw value)
        # in this case, the target isn't assign to or contained in anything.
        to_visit = queue([(None, None, None, target)])

#        primitive_types = (int, str, unicode, float, bool, date, time,
#                           datetime, list)

        # Breadth-first pre-order traversal insertion (to keep everything
        # within a single transaction)
        while len(to_visit) > 0:
            (parent_obj, parent_rslt, attr_name, value) = to_visit.popleft()

            # An object, add it's properties to the traversal queue
            if interfaces.IInstance.providedBy(value):
#                if not interfaces.Schema.providedBy(value):
#                    raise Exception("This object is not going to work out")

                schema_obj = list(providedBy(value))[0]

                schema_rslt = session.query(model.Schema)\
                              .filter_by(create_date=schema_obj.__version__)\
                              .join(model.Specification)\
                              .filter_by(name=schema_obj.__name__)\
                              .first()

                instance_rslt = model.Instance(
                    schema=schema_rslt,
                    title=u"%s-%d" % (schema_rslt.specification.name,
                                      currenttime()),
                    description=u""
                    )

                session.flush()

                value.__id__ = instance_rslt.id

                for name, field_obj in zope.schema.getFieldsInOrder(schema_obj):
                    child = getattr(value, name)
                    to_visit.append((value, instance_rslt, name, child,))

            else:

                attribute_rslt = session.query(model.Attribute)\
                                 .filter_by(name=unicode(attr_name))\
                                 .join(model.Schema)\
                                 .filter_by(id=parent_rslt.schema.id)\
                                 .first()

                type_name = attribute_rslt.field.type.title

                if type_name in (u"binary",):
                    Field = model.Binary
                elif type_name in (u"date", u"time", u"datetime"):
                    Field = model.Datetime
                elif type_name in (u"integer",):
                    Field = model.Integer
                elif type_name in (u"object",):
                    Field = model.Object
                elif type_name in (u"real",):
                    Field = model.Real
                elif type_name in (u"text", u"string"):
                    Field = model.String
                elif type_name in (u"selection"):
                    Field = model.Selection
                else:
                    raise Exception("Type '%s' unsupported."  % type_name)

                if not attribute_rslt.field.is_list:
                    value = [value]

                for v in value:
                    value_rslt = Field(
                        instance=parent_rslt,
                        attribute=attribute_rslt,
                        value=v
                        )

                    session.add(value_rslt)

        session.commit()

        return target

    put.__doc__ = interfaces.IDatastore["put"].__doc__

    def purge(self, key):
        raise NotImplementedError()

    purge.__doc__ = interfaces.IDatastore["purge"].__doc__

    def retire(self, key):
        # we're going to use the object as the key (or it's 'name')
        Session = named_session(self)
        session = Session()

        if isinstance(key, (str, unicode)):
            key = str(key)
        elif interfaces.IInstance.providedBy(key):
            key = key.__id__
        else:
            raise Exception("The object specified cannot be evaluated into "
                            "a object to search for")

        instance_rslt = session.query(model.Instance)\
                        .filter_by(id=key)\
                        .first()

        if instance_rslt:
            instance_rslt.is_active = False
            session.flush()

        return instance_rslt is not None

    retire.__doc__ = interfaces.IDatastore["retire"].__doc__

    def restore(self, key):
        # we're going to use the object as the key (or it's 'name')
        Session = named_session(self)
        session = Session()

        if isinstance(key, (str, unicode)):
            key = str(key)
        elif interfaces.IInstance.providedBy(key):
            key = key.__id__
        else:
            raise Exception("The object specified cannot be evaluated into "
                            "a object to search for")

        instance_rslt = session.query(model.Instance)\
                        .filter_by(id=key)\
                        .first()

        if instance_rslt:
            instance_rslt.is_active = True
            session.flush()

        return instance_rslt is not None

    restore.__doc__ = interfaces.IDatastore["restore"].__doc__

    def spawn(self, target, **kw):
        if isinstance(target, (str, unicode)):
            iface = self.schemata.get(target)
        elif target.extends(interfaces.Schema):
            iface = target
        else:
            raise Exception("This will not be found")

        obj = Instance()
        directlyProvides(obj, iface)

        setattr(obj, "__schema__", iface)

        for name in zope.schema.getFieldNamesInOrder(iface):
            setattr(obj, name, FieldProperty(iface[name]))
            obj.__dict__[name].__set__(obj, kw.get(name))

        return obj

    spawn.__doc__ = interfaces.IDatastore["spawn"].__doc__

DatastoreFactory = Factory(
    Datastore,
    title=_(u"Datastore implementation factory."),
    description=_(u"Creates an instance of a datastore implementation object. "
                   "Also notifies listeners of this creation.")
    )

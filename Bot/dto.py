from sqlalchemy import Column, Integer, String, MetaData, ForeignKey, Boolean, Float
from sqlalchemy.orm import declarative_base, relationship

meta = MetaData()
Base = declarative_base(metadata=meta)


class LocationType:
    TOWN = 'town'
    DUNGEON = 'dungeon'

    text_to_entry = {
        'town': TOWN,
        'dungeon': DUNGEON,
    }


class Location(Base):
    __tablename__ = 'location'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True,)
    x_coord = Column(Integer)
    y_coord = Column(Integer)
    location_type = Column(String(length=16))


class Person(Base):
    __tablename__ = 'person'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    nickname = Column(String(length=256))
    external_id = Column(String(length=128))
    level = Column(Integer)
    hp = Column(Integer)
    money = Column(Integer)
    attack = Column(Integer)
    magic = Column(Integer)
    magic_attack = Column(Integer)
    xp = Column(Integer)
    armour = Column(Integer)
    magic_armour = Column(Integer)
    location_id = Column(Integer, ForeignKey('location.id'))
    location = relationship(Location.__name__, foreign_keys='Person.location_id')


class AttackType:
    PHYSICAL = 'physical'
    MAGICAL = 'magical'

    text_to_entry = {
        'physical': PHYSICAL,
        'magical': MAGICAL,
    }


class Mob(Base):
    __tablename__ = 'mob'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    hp = Column(Integer)
    xp = Column(Integer)
    req_level = Column(Integer)
    attack_type = Column(String(length=16))
    attack = Column(Integer)
    armour = Column(Integer)
    magic_armour = Column(Integer)


class ItemType:
    WEAPON = 'weapon'
    ARMOR = 'armor'
    HELMET = 'helmet'
    BOOTS = 'boots'
    BRACERS = 'bracers'
    POTION = 'potion'

    text_to_entry = {
        'weapon': WEAPON,
        'armor': ARMOR,
        'helmet': HELMET,
        'boots': BOOTS,
        'bracers': BRACERS,
        'potion': POTION,
    }


class Item(Base):
    __tablename__ = 'item'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    cost = Column(Integer)
    cost_to_sale = Column(Integer)
    item_type = Column(String(length=16))
    hp = Column(Integer)
    mana = Column(Integer)
    attack = Column(Integer)
    magic_attack = Column(Integer)
    armour = Column(Integer)
    magic_armour = Column(Integer)
    req_level = Column(Integer)


class PersonItem(Base):
    __tablename__ = 'person_item'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)

    person_id = Column(Integer, ForeignKey('person.id'))
    person = relationship(Person.__name__, foreign_keys='PersonItem.person_id')

    item_id = Column(Integer, ForeignKey('item.id'))
    item = relationship(Item.__name__, foreign_keys='PersonItem.item_id')

    quantity = Column(Integer)
    put_on = Column(Boolean)


class Path(Base):
    __tablename__ = 'path'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)

    from_location_id = Column(Integer, ForeignKey('location.id'))
    from_location = relationship(Location.__name__, foreign_keys='Path.from_location_id')

    to_location_id = Column(Integer, ForeignKey('location.id'))
    to_location = relationship(Location.__name__, foreign_keys='Path.to_location_id')

    distance = Column(Integer)


class ItemInLocation(Base):
    __tablename__ = 'item_in_location'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)

    location_id = Column(Integer, ForeignKey('location.id'))
    location = relationship(Location.__name__, foreign_keys='ItemInLocation.location_id')

    item_id = Column(Integer, ForeignKey('item.id'))
    item = relationship(Item.__name__, foreign_keys='ItemInLocation.item_id')


class Journey(Base):
    __tablename__ = 'journey'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)

    person_id = Column(Integer, ForeignKey('person.id'))
    person = relationship(Person.__name__, foreign_keys='Journey.person_id')

    from_location_id = Column(Integer, ForeignKey('location.id'))
    from_location = relationship(Location.__name__, foreign_keys='Journey.from_location_id')

    to_location_id = Column(Integer, ForeignKey('location.id'))
    to_location = relationship(Location.__name__, foreign_keys='Journey.to_location_id')

    arrive_by = Column(Float)

import random
import sqlite3
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.future import select
from sqlalchemy.orm import Session, sessionmaker

from dto import meta, Location, LocationType, Mob, AttackType, ItemType, Item, ItemInLocation, Path

database_name = 'game.db'


class GameDataInitializer:
    def __init__(self, engine):
        self.Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    def generate_world(self):
        self._generate_locations()
        self._generate_mobs()
        self._generate_items()
        self._distribute_items()
        self._create_paths()

    def _generate_locations(self):
        locations = []
        existing_coord = set()
        for i in range(20):
            for type in LocationType.text_to_entry.values():
                x_coord, y_coord = (random.randint(0, 20), random.randint(0, 20))
                while (x_coord, y_coord) in existing_coord:
                    x_coord, y_coord = (random.randint(0, 20), random.randint(0, 20))
                locations.append(
                    Location(
                        x_coord=x_coord,
                        y_coord=y_coord,
                        location_type=type,
                    )
                )
                existing_coord.add((x_coord, y_coord))

        self._create_objects(locations)

    def _generate_mobs(self):
        mobs = []
        for req_level in range(1, 6):
            for attack_type in AttackType.text_to_entry.values():
                mobs.append(
                    Mob(
                        hp=req_level * 100,
                        xp=req_level * 25,
                        req_level=req_level,
                        attack_type=attack_type,
                        attack=req_level * random.randint(10, 15),
                        armour=req_level * random.randint(1 + req_level, 10),
                        magic_armour=req_level * random.randint(1 + req_level, 10),
                    )
                )

        self._create_objects(mobs)

    def _generate_items(self):
        items = []
        for req_level in range(1, 6):
            for item_type in ItemType.text_to_entry.values():
                items.append(
                    Item(
                        cost=req_level * 50,
                        cost_to_sale=req_level * 50 * 80 / 100,
                        item_type=item_type,
                        hp=req_level * 10,
                        mana=req_level * 10,
                        attack=req_level * random.randint(11, 16),
                        magic_attack=req_level * random.randint(11, 16),
                        armour=req_level * random.randint(2 + req_level, 11),
                        magic_armour=req_level * random.randint(2 + req_level, 11),
                        req_level=req_level,
                    )
                )
        self._create_objects(items)

    def _distribute_items(self):
        with self._new_session() as s:
            items: List[Item] = s.execute(select(Item)).scalars().all()
            locations: List[Location] = s.execute(select(Location).where(Location.location_type == LocationType.TOWN)).scalars().all()

        items_in_locations = []
        for item in items:
            for location in locations:
                if random.uniform(0, 1) >= (1 - 1.0 / item.req_level) or item.item_type == ItemType.POTION:
                    items_in_locations.append(
                        ItemInLocation(
                            location_id=location.id,
                            item_id=item.id,
                        )
                    )
        self._create_objects(items_in_locations)

    def _create_paths(self):
        with self._new_session() as s:
            locations: List[Location] = s.execute(select(Location)).scalars().all()

        paths = []
        for from_loc in locations:
            for to_loc in locations:
                if from_loc == to_loc:
                    continue

                distance = abs(from_loc.x_coord - to_loc.x_coord) + abs(from_loc.y_coord - to_loc.y_coord)
                if distance > 10:
                    continue

                paths.append(
                    Path(
                        from_location_id=from_loc.id,
                        to_location_id=to_loc.id,
                        distance=distance,
                    )
                )
        self._create_objects(paths)

    def _new_session(self) -> Session:
        return self.Session()

    def _create_objects(self, objects):
        with self._new_session() as s:
            s.add_all(objects)
            s.commit()


if __name__ == '__main__':
    sqlite3.connect(database_name).close()
    engine = create_engine(f'sqlite+pysqlite:///{database_name}', echo=True)

    meta.drop_all(engine)
    meta.create_all(engine)

    GameDataInitializer(engine=engine).generate_world()

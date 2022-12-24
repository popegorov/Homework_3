from typing import TypeVar, List

from sqlalchemy import and_, or_, desc, update, delete
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import selectinload

from dto import Location, Item, PersonItem, ItemType, Person, ItemInLocation, Path, Journey
from init_db import database_name


class GameAsyncDao:
    T = TypeVar("T")

    def __init__(self):
        self.engine = create_async_engine(f'sqlite+aiosqlite:///{database_name}', echo=False)
        self.AsyncSession = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def create_and_get(self, entry):
        async with self._new_session() as s:
            await self._create_and_get(s, entry)
        return entry

    async def get_by_id(self, table: T, id, references=[]) -> T:
        async with self._new_session() as s:
            query = select(table).where(table.id == id)
            for reference in references:
                query = query.options(selectinload(reference))
            return (await s.execute(query)).scalar()

    async def get_person_by_external_id(self, external_id):
        async with self._new_session() as s:
            query = select(Person)\
                .where(Person.external_id == external_id)\
                .order_by(desc(Person.id))\
                .limit(1)
            return (await s.execute(query)).scalar()

    async def delete(self, table: T, id):
        async with self._new_session() as s:
            stmt = delete(table).where(table.id == id)
            await s.execute(stmt)
            await s.commit()

    async def get_first_location(self):
        async with self._new_session() as s:
            query = select(Location).order_by(Location.id).limit(1)
            return (await s.execute(query)).scalar()

    async def get_first_weapon(self):
        async with self._new_session() as s:
            query = select(Item)\
                .where(and_(Item.req_level == 1, Item.item_type == ItemType.WEAPON))\
                .order_by(Item.attack)\
                .limit(1)
            return (await s.execute(query)).scalar()

    async def dispose(self):
        await self.engine.dispose()

    async def get_items(self, person_id, only_worn=False) -> List[PersonItem]:
        async with self._new_session() as s:
            query = select(PersonItem)\
                .options(selectinload(PersonItem.item))\
                .where(and_(PersonItem.person_id == person_id, or_(PersonItem.put_on, not only_worn)))\
                .order_by(desc(PersonItem.put_on))
            return (await s.execute(query)).scalars()

    async def get_person_item(self, person_id, item_id) -> PersonItem:
        async with self._new_session() as s:
            query = select(PersonItem)\
                .options(selectinload(PersonItem.item))\
                .where(and_(PersonItem.person_id == person_id, PersonItem.item_id == item_id))
            return (await s.execute(query)).scalar()

    async def get_all_items_in_location(self, location_id, person_level):
        async with self._new_session() as s:
            query = select(ItemInLocation)\
                .join(Item)\
                .options(selectinload(ItemInLocation.item))\
                .where(and_(ItemInLocation.location_id == location_id, Item.req_level <= person_level))
            items_in_location = (await s.execute(query)).scalars()
            return list(map(lambda x: x.item, items_in_location))

    async def get_item_in_location(self, item_id, location_id) -> ItemInLocation:
        async with self._new_session() as s:
            query = select(ItemInLocation)\
                .options(selectinload(ItemInLocation.item))\
                .where(and_(ItemInLocation.item_id == item_id, ItemInLocation.location_id == location_id))
            return (await s.execute(query)).scalar()

    async def update_person_item_put_on(self, person_item_id, put_on):
        async with self._new_session() as s:
            stmt = update(PersonItem)\
                .where(PersonItem.id == person_item_id)\
                .values(put_on=put_on)
            await s.execute(stmt)
            await s.commit()

    async def perform_transaction(
        self,
        person_id,
        balance_change,
        item_id,
        quantity_change,
    ):
        if self.sign(balance_change) == self.sign(quantity_change):
            return

        async with self._new_session() as s:
            await self._update_user_balance(s, person_id, balance_change)

            person_item = await self.get_person_item(person_id, item_id)
            new_quantity = (person_item.quantity if person_item is not None else 0) + quantity_change

            if (person_item is None and quantity_change < 0) or new_quantity < 0:
                s.rollback()
            elif person_item is None:
                await self._create_and_get(
                    session=s,
                    entry=PersonItem(
                        person_id=person_id,
                        item_id=item_id,
                        quantity=new_quantity,
                        put_on=False,
                    ),
                )
            elif new_quantity == 0:
                stmt = delete(PersonItem).where(PersonItem.id == person_item.id)
                await s.execute(stmt)
            else:
                stmt = update(PersonItem)\
                    .where(PersonItem.id == person_item.id)\
                    .values(quantity=new_quantity)
                await s.execute(stmt)
            await s.commit()

    async def get_available_paths(self, location_id) -> List[Path]:
        async with self._new_session() as s:
            query = select(Path)\
                .options(selectinload(Path.from_location))\
                .options(selectinload(Path.to_location))\
                .where(Path.from_location_id == location_id)
            return (await s.execute(query)).scalars()

    async def get_path_by_from_and_to_points(self, from_location_id, to_location_id):
        async with self._new_session() as s:
            query = select(Path)\
                .where(and_(Path.from_location_id == from_location_id, Path.to_location_id == to_location_id))
            return (await s.execute(query)).scalar()

    async def get_last_journey(self, person_id):
        async with self._new_session() as s:
            query = select(Journey)\
                .options(selectinload(Journey.from_location))\
                .options(selectinload(Journey.to_location))\
                .where(Journey.person_id == person_id)\
                .order_by(desc(Journey.arrive_by))
            return (await s.execute(query)).scalar()

    async def update_person_location_and_state(self, person_id, new_location_id, hp):
        async with self._new_session() as s:
            stmt = update(Person)\
                .where(Person.id == person_id)\
                .values(location_id=new_location_id, hp=hp)
            await s.execute(stmt)
            await s.commit()

    def _new_session(self) -> AsyncSession:
        return self.AsyncSession()

    @staticmethod
    async def _update_user_balance(session, person_id, balance_change):
        query = select(Person).where(Person.id == person_id)
        person = (await session.execute(query)).scalar()

        if person.money + balance_change < 0:
            session.rollback()

        stmt = update(Person)\
            .where(Person.id == person_id)\
            .values(money=person.money + balance_change)
        await session.execute(stmt)

    @staticmethod
    async def _create_and_get(session, entry):
        session.add(entry)
        await session.commit()
        await session.refresh(entry)

    @staticmethod
    def sign(x):
        if x > 0:
            return 1
        elif x < 0:
            return -1
        else:
            return 0
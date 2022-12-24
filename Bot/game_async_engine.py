from functools import reduce
from typing import List, Optional, Tuple
from textwrap import dedent
from time import time
from datetime import datetime

from dto import Person, Item, ItemType, PersonItem, Path, LocationType, Journey
from game_dao import GameAsyncDao


class PersonStatistics:
    def __init__(self, person: Person, worn_items: List[Item]):
        self.person = person
        self.worn_items = worn_items

    def compute_worn_by_property(self, property_getter):
        return reduce(lambda x, y: x + property_getter(y), self.worn_items, 0)

    def stat_string(self):
        return dedent(
            f"""\
            Current statistics:
            * Nickname: {self.person.nickname}
            * Level: {self.person.level}
            * HP: {self.person.hp}
            * XP: {self.person.xp}
            * Money: {self.person.money}
            * Attack: {self.person.attack} (+{self.compute_worn_by_property(lambda x: x.attack)})
            * Magic attack: {self.person.magic_attack} (+{self.compute_worn_by_property(lambda x: x.magic_attack)})
            * Armour: {self.person.armour} (+{self.compute_worn_by_property(lambda x: x.armour)})
            * Magic armour: {self.person.magic_armour} (+{self.compute_worn_by_property(lambda x: x.magic_armour)})
            * Location: {self.person.location.x_coord, self.person.location.y_coord}
            """
        )


class GameAsyncEngine:
    def __init__(self):
        self.dao = GameAsyncDao()

    async def init_person(self, nickname, external_id) -> Person:
        location = await self.dao.get_first_location()
        person = await self.dao.create_and_get(
            Person(
                nickname=nickname,
                external_id=external_id,
                level=1,
                hp=100,
                money=250,
                attack=50,
                magic=50,
                magic_attack=50,
                xp=0,
                armour=0,
                magic_armour=0,
                location_id=location.id,
            )
        )

        item = await self.dao.get_first_weapon()
        await self.dao.create_and_get(
            PersonItem(
                person_id=person.id,
                item_id=item.id,
                quantity=1,
                put_on=True,
            )
        )
        return person

    async def get_person(self, external_id) -> Person:
        return await self.dao.get_person_by_external_id(external_id)

    async def person_statistics(self, person_id) -> PersonStatistics:
        person = await self.dao.get_by_id(Person, person_id, references=[Person.location])
        worn_items = self._unwrap_items(await self.dao.get_items(person.id, only_worn=True))
        return PersonStatistics(person, worn_items)

    async def inventory(self, person_id) -> List[PersonItem]:
        return await self.dao.get_items(person_id)

    async def get_person_item(self, person_id, item_id) -> PersonItem:
        return await self.dao.get_person_item(person_id, item_id)

    async def put_on_item(self, person_id, item_id) -> Optional[str]:
        person_item = await self.dao.get_person_item(person_id, item_id)
        if not person_item:
            return 'no such item exists'
        elif person_item.put_on:
            return 'item is already worn'

        if person_item.item.item_type != ItemType.POTION:
            worn_items = self._unwrap_items(await self.dao.get_items(person_id, only_worn=True))
            items_with_current_type = list(filter(lambda x: x.item_type == person_item.item.item_type, worn_items))
            assert len(items_with_current_type) <= 1
            if len(items_with_current_type) == 1:
                await self.take_off_item(person_id, item_id=items_with_current_type[0].id)

        await self.dao.update_person_item_put_on(person_item.id, put_on=True)

    async def take_off_item(self, person_id, item_id) -> Optional[str]:
        person_item = await self.dao.get_person_item(person_id, item_id)
        if not person_item:
            return 'no such item exists'
        elif not person_item.put_on:
            return 'item is not worn'

        await self.dao.update_person_item_put_on(person_item.id, put_on=False)

    async def list_items_to_buy(self, person_id) -> Tuple[Optional[str], List[Item]]:
        person = await self.dao.get_by_id(Person, person_id, references=[Person.location])
        if person.location.location_type == LocationType.DUNGEON:
            return f'there are no shops in {LocationType.DUNGEON}', []
        return None, await self.dao.get_all_items_in_location(person.location_id, person.level)

    async def buy_item(self, person_id, item_id, quantity) -> Optional[str]:
        person = await self.dao.get_by_id(Person, person_id, references=[Person.location])
        if person.location.location_type == LocationType.DUNGEON:
            return f'there are no shops in {LocationType.DUNGEON}'

        item_in_location = await self.dao.get_item_in_location(item_id, person.location_id)
        if not item_in_location or person.level < item_in_location.item.req_level:
            return 'no such item in this location'

        buy_amount = quantity * item_in_location.item.cost
        if buy_amount > person.money:
            return 'insufficient funds'

        await self.dao.perform_transaction(
            person_id=person_id,
            balance_change=-buy_amount,
            item_id=item_id,
            quantity_change=quantity,
        )

    async def sell_item(self, person_id, item_id, quantity) -> Optional[str]:
        person = await self.dao.get_by_id(Person, person_id, references=[Person.location])
        if person.location.location_type == LocationType.DUNGEON:
            return f'there are no shops in {LocationType.DUNGEON}'

        person_item = await self.dao.get_person_item(person_id, item_id)
        if not person_item:
            return 'no such item exist'
        elif quantity > person_item.quantity:
            return "don't have so many items"

        await self.dao.perform_transaction(
            person_id=person_id,
            balance_change=quantity * person_item.item.cost_to_sale,
            item_id=item_id,
            quantity_change=-quantity,
        )

    async def get_available_paths(self, person_id) -> List[Path]:
        person = await self.dao.get_by_id(Person, person_id)
        return await self.dao.get_available_paths(person.location_id)

    async def start_journey(self, person_id, to_location_id) -> Tuple[bool, str]:
        person = await self.dao.get_by_id(Person, person_id)
        path = await self.dao.get_path_by_from_and_to_points(person.location_id, to_location_id)
        if not path:
            return True, "desired location can't be reached from here"

        journey = await self.dao.create_and_get(
            Journey(
                person_id=person_id,
                from_location_id=path.from_location_id,
                to_location_id=path.to_location_id,
                arrive_by=time() + path.distance,
            )
        )
        return False, str(datetime.fromtimestamp(journey.arrive_by))

    async def check_journey_and_update_person(self, person_id) -> Optional[str]:
        journey = await self.dao.get_last_journey(person_id)
        if not journey:
            return
        elif journey.arrive_by > time():
            return f'In journey. Should arrive by {datetime.fromtimestamp(journey.arrive_by)}'

        person = await self.dao.get_by_id(Person, person_id)
        if person.location_id == journey.from_location_id:
            await self.dao.update_person_location_and_state(
                person_id=person_id,
                new_location_id=journey.to_location_id,
                hp=100 if journey.to_location.location_type == LocationType.TOWN else person.hp,
            )

    @staticmethod
    def _unwrap_items(person_items) -> List[Item]:
        return list(map(lambda x: x.item, person_items))

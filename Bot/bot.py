from aiogram import Bot, Dispatcher, executor, types
from dto import Item
from game_async_engine import GameAsyncEngine
import os
import re
from textwrap import dedent

bot = Bot(token="")
dp = Dispatcher(bot)
engine = GameAsyncEngine()


def start_bot():
    executor.start_polling(dp)


async def _get_person_and_check_state_integrity(message: types.Message):
    person = await engine.get_person(str(message.from_user.id.real))
    if person is None:
        await message.reply("You haven't created a character yet. See /help for more info.")
        return
    journey_in_progress = await engine.check_journey_and_update_person(person.id)
    if journey_in_progress:
        await message.reply(journey_in_progress)
        return
    return person


async def _extract_item_id(message: types.Message):
    match = re.search(f'{message.get_command()}\\s+([0-9]+)*\\s*', message.text, re.IGNORECASE)
    if not match:
        await message.reply('Please, enter a correct item_id that you own.')
        return
    return match.group(1)


async def _extract_item_id_and_quantity(message: types.Message):
    match = re.search(f'{message.get_command()}\\s+([0-9]+)*\\s+([0-9]+)*\\s*', message.text, re.IGNORECASE)
    if not match:
        await message.reply('Please, enter a correct item_id and quantity')
        return
    return match.group(1), match.group(2)


def item_string(item: Item):
    return dedent(
        f"""\
        id: {item.id}
        cost: {item.cost}
        cost_to_sale: {item.cost_to_sale}
        item_type: {item.item_type}
        hp: {item.hp}
        mana: {item.mana}
        attack: {item.attack}
        magic_attack: {item.magic_attack}
        armour: {item.armour}
        magic_armour: {item.magic_armour}
        """
    )


@dp.message_handler(commands=['start', 'help'])
async def _help(message: types.Message):
    await message.answer(
        text=dedent(
            """\
            Welcome to our game! Here is the list of commands you can execute:
            /init_person [name] – Initializes your character. Subsequent call create a new one.
            /stats – Shows your character's statistics.
            /inventory – Shows what items your character has.
            /item_info [item_id] – Shows detailed item info.
            /put_on [item_id] – By this command you can wear an item with provided item_id.
            /take_off [item_id] – By this command you can take off an item with provided item_id.
            /shop – If you're currently in a town, you can buy or sell some items. This command says what goods are available here.
            /buy [item_id] [quantity] – Buy quantity items of provided item_id.
            /sell [item_id] [quantity] – Sell quantity items of provided item_id.
            /available_destinations – Check what locations are available to visit from your location.
            /start_journey [location_id] – Start journey to provided location_id.
            """
        ),
    )


@dp.message_handler(commands=['init_person'])
async def _init_person(message: types.Message):
    match = re.search('/init_person\\s+([a-z0-9]+)*\\s*', message.text, re.IGNORECASE)
    if not match:
        await message.reply('Please, enter a correct name. Names can only contain latin letters and numbers.')
        return
    nickname = match.group(1)
    await engine.init_person(nickname=nickname, external_id=str(message.from_user.id.real))
    await message.reply(f'You successfully created a character with name {nickname}.')


@dp.message_handler(commands=['stats'])
async def _stats(message: types.Message):
    person = await _get_person_and_check_state_integrity(message)
    if not person:
        return

    stats = await engine.person_statistics(person.id)
    await message.answer(stats.stat_string())


@dp.message_handler(commands=['inventory'])
async def _inventory(message: types.Message):
    person = await _get_person_and_check_state_integrity(message)
    if not person:
        return

    inventory = await engine.inventory(person.id)
    result = 'Your inventory:\n'
    for person_item in inventory:
        result += f'id={person_item.item_id} type={person_item.item.item_type} qty={person_item.quantity} worn={person_item.put_on}\n'
    await message.answer(result)


@dp.message_handler(commands=['item_info'])
async def _item_info(message: types.Message):
    person = await _get_person_and_check_state_integrity(message)
    if not person:
        return

    item_id = await _extract_item_id(message)
    if not item_id:
        return

    person_item = await engine.get_person_item(person.id, item_id)
    if not person_item:
        await message.reply('Please, enter a correct item_id that you own.')
        return
    item = person_item.item
    await message.answer(f'Item info:\n{item_string(item)}')


@dp.message_handler(commands=['put_on'])
async def _put_on(message: types.Message):
    person = await _get_person_and_check_state_integrity(message)
    if not person:
        return

    item_id = await _extract_item_id(message)
    if not item_id:
        return

    err = await engine.put_on_item(person.id, item_id)
    if err:
        await message.reply(f"Can't put on the item, because {err}.")
    else:
        await message.answer('Successfully put on the item.')


@dp.message_handler(commands=['take_off'])
async def _take_off(message: types.Message):
    person = await _get_person_and_check_state_integrity(message)
    if not person:
        return

    item_id = await _extract_item_id(message)
    if not item_id:
        return

    err = await engine.take_off_item(person.id, item_id)
    if err:
        await message.reply(f"Can't take off the item, because {err}.")
    else:
        await message.answer('Successfully put off the item.')


@dp.message_handler(commands=['shop'])
async def _shop(message: types.Message):
    person = await _get_person_and_check_state_integrity(message)
    if not person:
        return

    err, items = await engine.list_items_to_buy(person.id)
    if err:
        await message.reply(f"Can't shop here, because {err}")
        return

    res = 'Available items:\n'
    for item in items:
        res += '–' * 15 + '\n'
        res += item_string(item)

    await message.answer(res)


@dp.message_handler(commands=['buy'])
async def _buy(message: types.Message):
    person = await _get_person_and_check_state_integrity(message)
    if not person:
        return

    res = await _extract_item_id_and_quantity(message)
    if not res:
        return
    item_id, quantity = res

    err = await engine.buy_item(person.id, item_id, int(quantity))
    if err:
        await message.reply(f"Can't buy the item, because {err}")
    else:
        await message.answer('Successfully bought the item. Check the inventory and statistics.')


@dp.message_handler(commands=['sell'])
async def _sell(message: types.Message):
    person = await _get_person_and_check_state_integrity(message)
    if not person:
        return

    res = await _extract_item_id_and_quantity(message)
    if not res:
        return
    item_id, quantity = res

    err = await engine.sell_item(person.id, item_id, int(quantity))
    if err:
        await message.reply(f"Can't sell the item, because {err}")
    else:
        await message.answer('Successfully sold the item. Check the inventory and statistics.')


@dp.message_handler(commands=['available_destinations'])
async def _available_destinations(message: types.Message):
    person = await _get_person_and_check_state_integrity(message)
    if not person:
        return

    paths = await engine.get_available_paths(person.id)
    res = 'You can travel to:\n'
    for path in paths:
        res += '-' * 15 + '\n'
        res += dedent(
            f"""\
            id: {path.to_location_id}
            coordinates: {path.to_location.x_coord, path.to_location.y_coord}
            type: {path.to_location.location_type}
            distance: {path.distance}
            """
        )
    await message.answer(res)


@dp.message_handler(commands=['start_journey'])
async def _start_journey(message: types.Message):
    person = await _get_person_and_check_state_integrity(message)
    if not person:
        return

    match = re.search(f'{message.get_command()}\\s+([0-9]+)*\\s*', message.text, re.IGNORECASE)
    if not match:
        await message.reply('Please, enter a correct location_id where you want to go.')
        return
    location_id = match.group(1)

    (has_err, res_str) = await engine.start_journey(person.id, location_id)
    if has_err:
        await message.reply(f"Can't go to this location, because {res_str}")
    else:
        await message.answer(f'Started the journey. Should arrive at {res_str}')


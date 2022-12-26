## Functions:

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

## To run do:
1. pip3 install -r requirements.txt
2. python3 init_db.py
3. write TOKEN in bot.py
4. python3 main.py

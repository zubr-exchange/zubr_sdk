# Zubr exchange SDK
## Simple example
```python
import logging
from pprint import pprint

from zubr import ZubrSDK, OrderType, TimeInForce

zubr_sdk = ZubrSDK(
    api_key='YOUR-API-KEY-HERE',
    api_secret='YOUR-API-SECRET-HERE',
)

logging.basicConfig(level=logging.INFO)

context = {
    'order_placed': False,
    'sell_price': '0',
}


def sell_and_cancel(message):
    print(f'order placed: {message}')
    order_id = message['result']['value']

    # Cancel order
    zubr_sdk.cancel_order(
        order_id=order_id,
        callback=lambda x: (
            print(f'Order cancelled: {x}')
        ),
    )


def sell_and_replace(message):
    print(f'order placed: {message}')
    order_id = message['result']['value']

    # Replace order
    zubr_sdk.replace_order(
        order_id=order_id,
        price=context['sell_price'],
        size=2,
        callback=lambda x: (
            print(f'Order replaced: {x}')
        ),
    )


# Fetch orderbook
@zubr_sdk.subscribe_orderbook
def on_orderbook(message):
    print('orderbook:')
    pprint(message)

    if context['order_placed']:
        return

    instrument_id, orders = list(message['value'].items())[0]
    sell_price = max(x['price'] for x in orders['asks'])
    context['sell_price'] = sell_price

    # Place and replace
    zubr_sdk.sell(
        instrument_id=instrument_id,
        price=sell_price,
        size=1,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        callback=sell_and_replace,
    )

    # Place and cancel
    zubr_sdk.sell(
        instrument_id=instrument_id,
        price=sell_price,
        size=1,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        callback=sell_and_cancel,
    )

    context['order_placed'] = True


# Fetch last trades
@zubr_sdk.subscribe_last_trades
def on_last_trades(message):
    print('last trades:')
    pprint(message)


zubr_sdk.run_forever()
```
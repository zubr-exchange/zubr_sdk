# Zubr exchange SDK
## Simple example
```python
from pprint import pprint

from zubr import ZubrSDK, OrderType, TimeInForce

zubr_sdk = ZubrSDK(
    api_key='YOUR-API-KEY-HERE',
    api_secret='YOUR-API-SECRET-HERE',
)
context = {
    'order_placed': False,
    'sell_price': 0,
    'placed_order_id': '0',
}


def on_order_replaced(message):
    print(f'order replaced: {message}')

    # Cancel order
    order_id = context['placed_order_id']
    print(f'cancelling order with id={order_id!r}')
    zubr_sdk.cancel_order(
        order_id=order_id,
        callback=lambda x: print(
            f'order cancelled: {x}'
        )
    )


def on_order_placed(message):
    print(f'order placed: {message}')
    order_id = message['result']['value']
    context['placed_order_id'] = order_id

    # Replace order
    zubr_sdk.replace_order(
        order_id=order_id,
        price=context['sell_price'],
        size=2,
        callback=on_order_replaced,
    )


# Fetch orderbook
@zubr_sdk.subscribe_orderbook
def on_orderbook(message):
    print('orderbook:')
    pprint(message)

    if context['order_placed']:
        return

    instrument_id, orders = list(message['value'].items())[0]
    context['sell_price'] = max(x['price'] for x in orders['asks'])

    # Place order
    zubr_sdk.sell(
        instrument_id=instrument_id,
        price=context['sell_price'],
        size=1,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        callback=on_order_placed,
    )

    context['order_placed'] = True


@zubr_sdk.subscribe_last_trades
def on_last_trades(message):
    print('last trades:')
    pprint(message)


zubr_sdk.run_forever()
```
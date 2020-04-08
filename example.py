from datetime import datetime

from zubr import ZubrSDK, OrderType, TimeInForce


def main():
    zubr = ZubrSDK(
        api_key='YOUR-API-KEY-HERE',
        api_secret='YOUR-API-SECRET-HERE',
    )

    def on_instruments(message):
        for value in message['value'].values():
            print(f'got instrument {value["symbol"]}, {value["id"]}')

    def on_last_trades(message):
        if message['tag'] == 'err':
            print(f'an error occurred when handling last trades: {message}')
            return

        data = message['value']
        if data['type'] == 'snapshot':
            print('New snapshot!')
            print(data['payload'])
        elif data['type'] == 'trade':
            print('New trade!')
            print(data['payload'])
        else:
            print(f'unknown type of trade: {data["type"]}')

    def on_orderbook(message):
        print(f'on_orderbook: {message}')

    def on_orders(message):
        print(f'on_orders: {message}')

    def on_candles(message):
        print(f'on_candles: {message}')

    def on_order_fills(message):
        print(f'on_order_fills: {message}')

    def on_error(error):
        print('Error:', error)

    zubr.subscribe_errors(on_error)
    zubr.subscribe_orders(on_orders)
    zubr.subscribe_order_fills(on_order_fills)
    zubr.subscribe_instruments(on_instruments)
    zubr.subscribe_last_trades(on_last_trades)
    zubr.subscribe_orderbook(on_orderbook)
    zubr.subscribe_candles(
        instrument_id=1,
        resolution='1',
        callback=on_candles
    )

    zubr.get_candles_range(
        instrument_id=1,
        resolution='1',
        timestamp_from=int(datetime.utcnow().timestamp()),
        timestamp_to=int(datetime.utcnow().timestamp()) + 100,
        callback=lambda message: (
            print(f'get_candles_range: {message}')
        )
    )

    zubr.buy(
        instrument_id=2,
        price="1003.8",
        size=1,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        callback=lambda message: (
            print('buy', message)
        )
    )

    zubr.sell(
        instrument_id=2,
        price="1003.8",
        size=123,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        callback=lambda message: (
            print('sell', message)
        )
    )

    zubr.cancel_order(
        order_id='123456789',
        callback=lambda message: (
            print('cancel order', message)
        )
    )

    zubr.replace_order(
        order_id='123456789',
        price=123,
        size=1,
        callback=lambda message: (
            print('replace order', message)
        )
    )

    try:
        zubr.run_forever()
    except KeyboardInterrupt:
        print('Have a nice day!')


if __name__ == '__main__':
    main()

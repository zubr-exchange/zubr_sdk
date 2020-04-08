import hashlib
import json
import logging
from datetime import timezone, datetime
from decimal import Decimal
from enum import IntEnum, Enum
from hmac import HMAC
from typing import Callable, Union, Dict, Optional

from websocket import WebSocketApp

__all__ = {
    "ZubrSDK",
    'ZubrSDKError',
    'ZubrSDKLoginError',
    'OrderSide',
    'OrderType',
    'TimeInForce',
}

logger = logging.getLogger(__name__)


class ZubrSDKError(Exception):
    """
    Common ZubrSDK error
    """

    def __init__(self, message, code=None, response=None):
        super().__init__(message)

        self.message = message
        self.code = code
        self.response = response


class ZubrSDKLoginError(ZubrSDKError):
    """
    This exception is raised when login credentials are wrong
    """


class _Method(IntEnum):
    CHANNEL = 1
    RPC = 9


def _decode_decimal(encoded_decimal: dict):
    """
    Decodes decimal from internal format
    """
    return Decimal(
        encoded_decimal['mantissa']
    ).scaleb(
        encoded_decimal['exponent']
    )


def _encode_decimal(value: Union[Decimal, int, str]):
    """
    Encodes decimal into internal format
    """
    value = Decimal(value)
    exponent = value.as_tuple().exponent
    mantissa = int(value.scaleb(-exponent))

    return {
        'mantissa': mantissa,
        'exponent': exponent
    }


def _decode_response(response: Union[dict, list]) -> Union[dict, list]:
    """
    Decodes internal decimal representation into decimal.Decimal()
    """
    if isinstance(response, dict):
        if 'mantissa' in response and 'exponent' in response:
            return _decode_decimal(response)
        else:
            for key, value in response.items():
                response[key] = _decode_response(value)

            return response
    elif isinstance(response, list):
        for item in response:
            _decode_response(item)

    return response


def login_required(fn) -> Callable:
    def wrap(self, *args, **kwargs):
        if not (self._api_key and self._api_secret):
            raise ZubrSDKError(
                'Login required to perform this operation'
            )
        return fn(self, *args, **kwargs)

    return wrap


CallbackType = Callable[[Dict], None]


class OrderType(str, Enum):
    LIMIT = 'LIMIT'
    POST_ONLY = 'POST_ONLY'


class OrderSide(str, Enum):
    BUY = 'BUY'
    SELL = 'SELL'


class TimeInForce(str, Enum):
    SESSION = 'SESSION'
    GTC = 'GTC'
    IOC = 'IOC'
    FOK = 'FOK'


class ZubrSDK:
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        api_url='wss://zubr.io/api/v1/ws',
        default_callback: CallbackType = None,
    ):
        self._api_key: str = api_key
        self._api_secret: str = api_secret
        self._api_url: str = api_url.rstrip('/')

        self._logged_in: bool = False
        self._message_id: int = 0

        self._channel_callbacks: Dict[str, CallbackType] = {}
        self._message_callbacks: Dict[str, CallbackType] = {}
        self._error_callback: Optional[CallbackType] = None
        self._default_callback: Optional[CallbackType] = default_callback
        self._delayed_requests = []


        self._ws_app: WebSocketApp = WebSocketApp(
            api_url,
            header=[
                "User-Agent: ZubrSDK",
            ],
            on_open=self._on_open,
            on_message=self._on_message,
        )
        self._ws_open: bool = False

    def _resubscribe(self):
        channel_callbacks = self._channel_callbacks
        self._channel_callbacks = {}

        for channel, callback in channel_callbacks.items():
            self._subscribe(channel, callback)

    def subscribe_errors(self, callback: CallbackType):
        """
        Callback will be called when server sends response errors
        """
        self._error_callback = callback

    def subscribe_orders(self, callback: CallbackType):
        self._subscribe('orders', callback)

    def subscribe_order_fills(self, callback: CallbackType):
        self._subscribe('orderFills', callback)

    def subscribe_instruments(self, callback: CallbackType):
        self._subscribe('instruments', callback)

    def subscribe_last_trades(self, callback: CallbackType):
        self._subscribe('lasttrades', callback)

    def subscribe_orderbook(self, callback: CallbackType):
        self._subscribe(f'orderbook', callback)

    def subscribe_balance(self, callback: CallbackType):
        self._subscribe(f'balance', callback)

    def subscribe_candles(self, instrument_id: int, resolution: str, callback: CallbackType):
        self._subscribe(f'candles:{instrument_id}:{resolution}', callback)

    @login_required
    def place_order(
        self,
        instrument_id: int,
        price: Union[Decimal, int, str],
        size: int,
        order_type: OrderType,
        time_in_force: TimeInForce,
        side: OrderSide,
        callback: CallbackType,
    ):
        """
        :param instrument_id: int
        :param price: one of: Decimal, int, str
        :param size: int
        :param order_type: one of: 'LIMIT', 'POST_ONLY'
        :param time_in_force: one of: 'GTC', 'IOC', 'FOK'
        :param side: one of: 'BUY', 'SELL'
        :param callback: function that will be called when server sends place_order response
        :return: None
        """
        return self._rpc(
            method='placeOrder',
            params={
                'instrument': instrument_id,
                'price': _encode_decimal(price),
                'size': size,
                'type': order_type,
                'timeInForce': time_in_force,
                'side': side,
            },
            callback=callback
        )

    @login_required
    def replace_order(
        self,
        order_id: str,
        price: Union[Decimal, int, str],
        size: int,
        callback: CallbackType,
    ):
        return self._rpc(
            method='replaceOrder',
            params={
                'orderId': order_id,
                'price': _encode_decimal(price),
                'size': size,
            },
            callback=callback
        )

    @login_required
    def buy(
        self,
        instrument_id: int,
        price: Union[Decimal, int, str],
        size: int,
        order_type: OrderType,
        time_in_force: TimeInForce,
        callback: CallbackType,
    ):
        """
        Places a buy order
        Shortcut for place_order method
        """
        return self.place_order(
            instrument_id=instrument_id,
            price=price,
            size=size,
            order_type=order_type,
            time_in_force=time_in_force,
            callback=callback,
            side=OrderSide.BUY,
        )

    @login_required
    def sell(
        self,
        instrument_id: int,
        price: Union[Decimal, int, str],
        size: int,
        order_type: OrderType,
        time_in_force: TimeInForce,
        callback: CallbackType,
    ):
        """
        Places a sell order
        Shortcut for place_order method
        """
        return self.place_order(
            instrument_id=instrument_id,
            price=price,
            size=size,
            order_type=order_type,
            time_in_force=time_in_force,
            callback=callback,
            side=OrderSide.SELL,
        )

    @login_required
    def cancel_order(
        self,
        order_id: str,
        callback: CallbackType
    ):
        return self._rpc(
            method='cancelOrder',
            params=order_id,
            callback=callback
        )

    def get_candles_range(
        self,
        instrument_id: int,
        resolution: str,
        timestamp_from: int,
        timestamp_to: int,
        callback: CallbackType
    ):
        return self._rpc(
            'getCandlesRange', {
                "instrumentId": instrument_id,
                "resolution": resolution,
                "from": timestamp_from,
                "to": timestamp_to
            },
            callback=callback
        )

    def run_forever(self):
        self._ws_app.run_forever(
            ping_interval=15,
            suppress_origin=True
        )

    @staticmethod
    def _encode_hmac_message(message):
        buffer = []

        for key in sorted(message.keys()):
            buffer.append(f'{key}={message[key]}')

        return ';'.join(buffer).encode('utf-8')

    def _on_login(self, response: dict):
        if 'error' in response:
            raise ZubrSDKError(
                'An error occurred when logging in',
                response=response
            )

        result = response['result']

        if result['tag'] == 'err':
            raise ZubrSDKLoginError(
                'Wrong credentials',
                code=result.get('value', {}).get('code')
            )

        self._logged_in = True
        self._send_delayed_requests()

    def _try_login(self):
        """
        Tries to log in if credentials presented
        """
        if not (self._api_key and self._api_secret):
            self._send_delayed_requests()
            return

        utc_now = datetime.now(timezone.utc)
        timestamp = int(utc_now.timestamp())

        auth_code = HMAC(
            key=bytes.fromhex(self._api_secret),
            msg=self._encode_hmac_message({
                'key': self._api_key,
                'time': timestamp,
            }),
            digestmod=hashlib.sha256
        ).digest().hex()

        self._rpc(
            'loginSessionByApiToken',
            {
                'apiKey': self._api_key,
                'time': {
                    'seconds': timestamp,
                    'nanos': 0
                },
                'hmacDigest': auth_code,
            },
            callback=self._on_login
        )

    def _send_delayed_requests(self):
        delayed_requests = self._delayed_requests
        self._delayed_requests = []

        for request in delayed_requests:
            self._ws_app.send(request)

    def _create_request(
        self,
        method: _Method,
        params: dict,
    ) -> dict:
        """
        Creates request message
        """
        self._message_id += 1

        return {
            'id': self._message_id,
            'method': method,
            'params': params
        }

    def _subscribe(self, channel: str, callback: CallbackType):
        """
        Subscribes to the given channel
        """
        if channel in self._channel_callbacks:
            raise Exception(
                f'Already subscribed to channel {channel!r}'
            )

        self._channel_callbacks[channel] = callback
        request = self._create_request(
            _Method.CHANNEL,
            {'channel': channel}
        )
        self._send(request)

    def _send(self, request: dict):
        request = json.dumps(request)

        if self._ws_open:
            self._ws_app.send(request)
        else:
            self._delayed_requests.append(request)

    def _rpc(
        self,
        method: str,
        params=None,
        callback: CallbackType = None
    ):
        """
        Sends rpc request to the server
        """
        request = self._create_request(
            _Method.RPC,
            {
                "data": {
                    "method": method,
                    "params": params or {}
                }
            }
        )

        if callback:
            self._message_callbacks[request['id']] = callback

        self._send(request)

    def _on_open(self):
        self._ws_open = True
        self._try_login()

    def _on_message(
        self,
        message: str,
    ):
        data = json.loads(message)
        data = _decode_response(data)

        if 'id' in data:
            callback = self._message_callbacks.pop(data['id'], None)

            if callback:
                callback(data)
        elif 'error' in data:
            error_message = data['error'].get('message')
            error_code = data['error'].get('code')

            if self._error_callback is None:
                raise ZubrSDKError(
                    f'Server sent error: {error_message or error_code}',
                    code=error_code,
                    response=data
                )
            else:
                self._error_callback(data)
        elif 'channel' in data['result']:
            result: dict = data['result']
            channel_key = result['channel']
            data = result['data']

            try:
                channel_handler = self._channel_callbacks[channel_key]
            except KeyError:
                pass
            else:
                channel_handler(data)
        elif self._default_callback:
            self._default_callback(data)

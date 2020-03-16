# Zubr exchange SDK
## Simple example
```python
from zubr import ZubrSDK

zubr = ZubrSDK(
    api_key='YOUR-API-KEY-HERE',
    api_secret='YOUR-API-SECRET-HERE',
    default_callback=lambda message: (
        print('New message: ', message)
    )
)

def on_instruments(message):
    for value in message['value'].values():
        print(f'instrument {value["symbol"]}, {value["id"]}')

zubr.subscribe_instruments(on_instruments)
zubr.run_forever()
```
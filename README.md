<p align="center">
  <a href="https://github.com/love-apples/maxapi"><img src="logo.png" alt="MaxAPI"></a>
</p>


<p align="center">
<a href='https://max.ru/join/IPAok63C3vFqbWTFdutMUtjmrAkGqO56YeAN7iyDfc8'>MAX Чат</a> •
<a href='https://t.me/maxapi_github'>TG Чат</a>
</p>

<p align="center">
<a href='https://pypi.org/project/maxapi/'>
  <img src='https://img.shields.io/pypi/v/maxapi.svg' alt='PyPI version'></a>
<a href='https://pypi.org/project/maxapi/'>
  <img src='https://img.shields.io/pypi/pyversions/maxapi.svg' alt='Python Version'></a>
<a href='https://love-apples/maxapi/blob/main/LICENSE'>
  <img src='https://img.shields.io/github/license/love-apples/maxapi.svg' alt='License'></a>
</p>


## ● Документация и примеры использования

Можно посмотреть здесь: https://love-apples.github.io/maxapi/

## ● Установка из PyPi

Стабильная версия

```bash
pip install maxapi
```

## ● Установка из GitHub

Свежая версия, возможны баги. Рекомендуется только для ознакомления с новыми коммитами.

```bash
pip install git+https://github.com/max92110/maxapi.git
```



## ● Быстрый старт

Если вы тестируете бота в чате - не забудьте дать ему права администратора!

### ● Запуск Polling

Если у бота установлены подписки на Webhook - события не будут приходить при методе `start_polling`. При таком случае удалите подписки на Webhook через `await bot.delete_webhook()` перед `start_polling`.

```python
import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated

logging.basicConfig(level=logging.INFO)

# Внесите токен бота в переменную окружения MAX_BOT_TOKEN
# Не забудьте загрузить переменные из .env в os.environ
# или задайте его аргументом в Bot(token='...')
bot = Bot()
dp = Dispatcher()

# Ответ бота при нажатии на кнопку "Начать"
@dp.bot_started()
async def bot_started(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text='Привет! Отправь мне /start'
    )

# Ответ бота на команду /start
@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    await event.message.answer(f"Пример чат-бота для MAX 💙")


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
```

### ● Запуск Webhook

Перед запуском бота через Webhook, вам нужно установить дополнительные зависимости (fastapi, uvicorn). Можно это сделать через команду:
```bash
pip install maxapi[webhook]
```

Указан пример простого запуска, для более низкого уровня можете рассмотреть [этот пример](https://love-apples.github.io/maxapi/examples/#_6).
```python
import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated

logging.basicConfig(level=logging.INFO)

bot = Bot()
dp = Dispatcher()


# Команда /start боту
@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    await event.message.answer(f"Привет из вебхука!")


async def main():
    await dp.handle_webhook(
        bot=bot, 
        host='localhost',
        port=8080,
        log_level='critical' # Можно убрать для подробного логгирования
    )


if __name__ == '__main__':
    asyncio.run(main())
```

Пример для запуска с fastapi
```python
from contextlib import asynccontextmanager

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated
from maxapi.methods.types.getted_updates import process_update_webhook
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI, status
import redis.asyncio as redis

redis_client = redis.from_url(
            f'redis://{REDIS_URL}:{REDIS_PORT}/{REDIS_DB}'
        )

dp = Dispatcher(redis_client=redis_client, redis_prefix='maxapi:context')

bot = Bot(MAX_TOKEN)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        bot_status = await bot.get_me()
        print(f'Bot status: {bot_status}')
        yield
    finally:
        print('Finishing lifespan')



app = FastAPI(
    title='max_bot',
    docs_url='/api/v1/openapi',
    openapi_url='/api/v1/openapi.json',
    root_path='/maxapi/',
    lifespan=lifespan,
)

# Регистрация обработчика для вебхука
@app.post('/webhook')
async def _(request: Request):
    # Сериализация полученного запроса
    event_json = await request.json()
    # Десериализация полученного запроса в pydantic
    event_object = await process_update_webhook(
        event_json=event_json,
        bot=bot
    )
    try:
        await dp.handle(event_object)
    except Exception as e:
        print(f'Ошибка при обработке вебхука: {e}')
    finally:
        # Выходим в любом случае, не ждем повторной обработки
        return JSONResponse(content={'ok': True}, status_code=200)


# Ответ бота на команду /start
@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    await event.message.answer(f"Пример чат-бота для MAX 💙")

```
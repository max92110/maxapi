import asyncio
import json
from typing import Any, Dict, Optional, Union, TYPE_CHECKING

from ..context.state_machine import State, StatesGroup

if TYPE_CHECKING:
    from redis.asyncio import Redis


class MemoryContext:
    """
    Контекст хранения данных пользователя с блокировками.

    Args:
        chat_id (Optional[int]): Идентификатор чата
        user_id (Optional[int]): Идентификатор пользователя
    """

    def __init__(
        self,
        chat_id: Optional[int],
        user_id: Optional[int],
        redis_client: Optional["Redis[Any]"] = None,
        redis_prefix: str = "maxapi:context",
        redis_ttl: Optional[int] = None,
    ):
        self.chat_id = chat_id
        self.user_id = user_id
        self._context: Dict[str, Any] = {}
        self._state: State | str | None = None
        self._lock = asyncio.Lock()
        self._redis = redis_client
        self._redis_prefix = redis_prefix.rstrip(":")
        self._redis_ttl = redis_ttl

    def _key(self, kind: str) -> str:
        chat = "none" if self.chat_id is None else str(self.chat_id)
        user = "none" if self.user_id is None else str(self.user_id)
        return f"{self._redis_prefix}:{kind}:{chat}:{user}"

    @staticmethod
    def _serialize_state(state: Optional[Union[State, str]]) -> Optional[str]:
        if state is None:
            return None
        if isinstance(state, State):
            return state.name
        return str(state)

    @staticmethod
    def _restore_state(state_name: str | None) -> Optional[State | str]:
        if not state_name:
            return None

        for group in StatesGroup.__subclasses__():
            for attr in dir(group):
                candidate = getattr(group, attr)
                if isinstance(candidate, State) and str(candidate) == state_name:
                    return candidate

        state = State()
        state.name = state_name
        return state

    async def get_data(self) -> dict[str, Any]:
        """
        Возвращает текущий контекст данных.

        Returns:
            Словарь с данными контекста
        """

        async with self._lock:
            if not self._redis:
                return self._context

            raw = await self._redis.get(self._key("data"))
            if raw is None:
                return {}

            if isinstance(raw, bytes):
                raw = raw.decode()

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}

    async def set_data(self, data: dict[str, Any]):
        """
        Полностью заменяет контекст данных.

        Args:
            data: Новый словарь контекста
        """

        async with self._lock:
            if not self._redis:
                self._context = data
            else:
                await self._redis.set(
                    self._key("data"),
                    json.dumps(data, default=str),
                    ex=self._redis_ttl,
                )

    async def update_data(self, **kwargs: Any) -> None:
        """
        Обновляет контекст данных новыми значениями.

        Args:
            **kwargs: Пары ключ-значение для обновления
        """

        async with self._lock:
            if not self._redis:
                self._context.update(kwargs)
            else:
                raw = await self._redis.get(self._key("data"))

                if raw is None:
                    current = {}
                else:
                    if isinstance(raw, bytes):
                        raw = raw.decode()

                    try:
                        current = json.loads(raw)
                    except json.JSONDecodeError:
                        current = {}

                current.update(kwargs)
                await self._redis.set(
                    self._key("data"),
                    json.dumps(current, default=str),
                    ex=self._redis_ttl,
                )

    async def set_state(self, state: Optional[Union[State, str]] = None):
        """
        Устанавливает новое состояние.

        Args:
            state: Новое состояние или None для сброса
        """

        async with self._lock:
            serialized_state = self._serialize_state(state)

            if not self._redis:
                self._state = state
            else:
                key = self._key("state")
                if serialized_state is None:
                    await self._redis.delete(key)
                else:
                    await self._redis.set(
                        key, serialized_state, ex=self._redis_ttl
                    )

                self._state = self._restore_state(serialized_state)

    async def get_state(self) -> Optional[State | str]:
        """
        Возвращает текущее состояние.

        Returns:
            Текущее состояние или None
        """

        async with self._lock:
            if not self._redis:
                return self._state

            raw = await self._redis.get(self._key("state"))

            if raw is None:
                self._state = None
                return None

            if isinstance(raw, bytes):
                raw = raw.decode()

            restored = self._restore_state(raw)
            self._state = restored
            return restored

    async def clear(self):
        """
        Очищает контекст и сбрасывает состояние.
        """

        async with self._lock:
            self._state = None
            self._context = {}
            if self._redis:
                await self._redis.delete(self._key("data"))
                await self._redis.delete(self._key("state"))

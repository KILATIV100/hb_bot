# utils/album_middleware.py
import asyncio
from typing import Any, Dict, Union, List, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message

class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: float = 0.5):
        self.latency = latency
        self.album_data = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Якщо повідомлення не має media_group_id, це звичайне повідомлення
        if not event.media_group_id:
            return await handler(event, data)

        group_id = event.media_group_id

        if group_id not in self.album_data:
            self.album_data[group_id] = []
            asyncio.create_task(self.process_album(group_id, handler, event, data))

        self.album_data[group_id].append(event)
        # Ми не повертаємо handler тут, щоб зупинити обробку окремих повідомлень
        return

    async def process_album(self, group_id, handler, event, data):
        # Чекаємо, поки зберуться всі частини альбому
        await asyncio.sleep(self.latency)

        if group_id in self.album_data:
            album = self.album_data.pop(group_id)
            # Сортуємо за ID, щоб зберегти порядок
            album.sort(key=lambda x: x.message_id)
            
            # Передаємо список повідомлень (альбом) у хендлер
            data["album"] = album
            await handler(event, data)

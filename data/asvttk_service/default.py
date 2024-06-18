from aiogram.types import Message, Chat


DEFAULT_TRAINING_START_MSG = Message(message_id=1, chat=Chat(id=0, type="default"), text="Добро пожаловать на курс!",
                                     date=0)

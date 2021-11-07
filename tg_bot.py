import logging
import sqlite3
import aiogram.utils.markdown as md

from settings import API_TOKEN
from aiogram.types import ReplyKeyboardMarkup
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from datetime import datetime


logging.basicConfig(level=logging.INFO)


users_list = []
show_users = []

bot = Bot(token=API_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


#States
class User(StatesGroup):
    first_name = State()
    last_name = State()
    start_job = State()
    finish_job = State()
    kind_job = State()

#States
class ShowUser(StatesGroup):
    last_n = State()
    first_n = State()


@dp.message_handler(commands='start', state=None)
async def cmd_start(message: types.Message):
    await message.answer("Привет, меня зовут TimeWork.\nЯ телеграмм бот. Я запоминаю время начала и конца работы. А так же запоминаю вид работы, которой ты занимался. Время я запоминаю по всемирному координированному времени. Для того,чтобы узнать время в городе, в котором ты работал, тебе нужно узнать разницу по времени и прибавить к тому времени,которое я тебе выведу. Начнем заполнять данные.\nДля начала введи свое имя: ")
    # Set state
    await User.first_name.set()


@dp.message_handler(state=User.first_name)
async def input_fname(message: types.Message):
    First_name = message.text
    user_id = message.from_user.id
    users_list.append(user_id)
    users_list.append(First_name)

    await message.answer("Отлично, теперь введи свою фамилию: ")
    await User.next()


@dp.message_handler(state=User.last_name)
async def input_lname(message: types.Message):
    Last_name = message.text
    users_list.append(Last_name)

    # Configure ReplyKeyboardMarkup
    sj = ReplyKeyboardMarkup(resize_keyboard=True, selective=True, one_time_keyboard=True)
    sj.add('Я начал работать!')


    await message.answer("Ты уже начал работать?", reply_markup=sj)
    await User.next()


@dp.message_handler(lambda message: message.text not in ["Я начал работать!"], state=User.start_job)
async def process_sj_invalid(message: types.Message):
    return await message.reply("Для того чтобы перейти к следующему шагу, нажми на кнопку.")


@dp.message_handler(state=User.start_job)
async def start_job(message: types.Message):
    sj = datetime.utcnow()
    Start_job = sj.strftime("%H:%M:%S")
    users_list.append(Start_job)

    # Configure ReplyKeyboardMarkup
    fj = ReplyKeyboardMarkup(resize_keyboard=True, selective=True, one_time_keyboard=True)
    fj.add('Я закончил работать!')


    await message.answer("Ты уже закончил работать?", reply_markup=fj)
    await User.next()


@dp.message_handler(lambda message: message.text not in ["Я закончил работать!"], state=User.finish_job)
async def process_fj_invalid(message: types.Message):
    return await message.reply("Нажми кнопку, чтобы продолжить.")


@dp.message_handler(state=User.finish_job)
async def finish_job(message: types.Message):
    fj = datetime.utcnow()
    Finish_job = fj.strftime("%H:%M:%S")
    users_list.append(Finish_job)
    dj = datetime.utcnow()
    Date_job = dj.strftime("%d/%m/%Y")
    users_list.append(Date_job)

    await message.answer("Отлично,а теперь введи, чем ты занимался в это время: ")
    await User.next()


@dp.message_handler(state=User.kind_job)
async def input_kjob(message: types.Message, state: FSMContext):
    Kind_job = message.text
    users_list.append(Kind_job)

    await message.answer("Вы успешно ввели все данные.\nЯ записал все твои данные. Если ты захочешь посмотреть, чем ты занимался и в какое время, то напиши мне /show. ")

    #Create the database
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER,
    user_firstname TEXT,
    user_lastname TEXT,
    start_job INTEGER,
    finish_job INTEGER,
    date_job INTEGER,
    kind_job TEXT
    )
    """)
    #Input info into the database
    connect_insert = """INSERT INTO users 
                 (user_id, user_firstname, user_lastname, start_job, finish_job, date_job, kind_job)
                 VALUES (?,?,?,?,?,?,?);"""

    cursor.execute(connect_insert, users_list)
    connect.commit()
    cursor.close()
    users_list.clear()

    # Finish conversation
    await state.finish()


@dp.message_handler(commands='help')
async def cmd_help(message: types.Message):
    await message.answer("Привет, напиши /start и ты узнаешь, как я могу тебе помочь. Там я описал все свои функции.")


@dp.message_handler(commands='show', state=None)
async def cmd_show(message: types.Message):
    await message.answer("Для того, чтобы я вывел тебе информацию по твоей работе и твоему времени.\nВведи свою фамилию:")
    await ShowUser.last_n.set()


@dp.message_handler(state=ShowUser.last_n)
async def show_lastn(message: types.Message, state: FSMContext):
    #Connect with the database
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()

    Last_n = message.text
    show_users.append(Last_n)

    #Check by LastName
    show_select = """select * from users where user_lastname = ?"""
    cursor.execute(show_select, show_users)
    records = cursor.fetchall()

    if len(records) > 0:
        for row in records:
            name = row[1]
            lastn = row[2]
            sj = row[3]
            fj = row[4]
            date = row[5]
            kindjob = row[6]
            await bot.send_message(
                message.chat.id,
                md.text(
                    md.text('Имя:', name),
                    md.text('Фамилия:', lastn),
                    md.text('Время начала работы:', sj),
                    md.text('Время конца работы:', fj),
                    md.text('Дата работы:', date),
                    md.text('Вид работы:', kindjob),
                    sep='\n',
                    ),)
    else:
        await message.answer("Твоей фамилии нет в базе данных, проверь свою фамилию, а затем напиши еще раз /show и введи свою фамилию, если проверил и ввел все верно.")

    cursor.close()
    show_users.clear()

    # Finish conversation
    await state.finish()


@dp.message_handler()
async def msg(message: types.Message):
    await message.answer("Ты пишешь что-то непонятное.\nДля того, чтобы я тебя понял и смог помочь тебе напиши /help.\nА чтобы узнать, как я могу тебе помочь напиши /start.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)




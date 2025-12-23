from MultiEnvEmployer import Employer, RemoteModule, errors

emp = Employer(
    r"example_project",  # Путь к директории модуля
    r"py_venv/py311",  # Путь к виртуальному окружению
    picle_protocol=4  # Протокол связи picle
)

moduleA = RemoteModule(
    emp,  # Employer()
    "moduleA",  # Название файла "moduleA" ("moduleA.py")
    "terminal",  # "terminal", "logger", "terminal|logger", "none"
    caching=False,  # Кэшировать или нет, кэшируются только "RESULT"
    timeout_seconds=60,  # Время до отключения
    timeout_mode="progress"  # "none", "absolute", "progress"
)

emp.cache_clear()  # Отчистка кэша

# остановка процессов
emp.close()  # остановка всего
emp.close(moduleA.add)  # остановка одного процесса
emp.close([moduleA.add, moduleA.add])  # остановка списка процессов
# можно и так указывать
emp.close("moduleA.add")  # остановка одного процесса
emp.close(["moduleA.add", "moduleA.add"])  # остановка списка процессов

print(moduleA.__remote__.functions)  # Вывод всех функций и их сигнатур и описаний

# обычные функции
print(moduleA.add(2, 4))  # args
print(moduleA.multiply(a=3, b=7))  # kwargs

print(moduleA.tt(3))  # Пример перехвата print

print(moduleA.non())  # Пример функции без возврата ответа -> None

print(moduleA.async_test(1, 11))  # Возможно запускать асинхронные функции модуля

print(moduleA.test_imp_file(1, 2, 2))  # Проверка импорта файлов (file2mod.py)


# генератор с ошибкой так как останавливаем процесс
try:
    for x in moduleA.stream_numbers(5):
        print("stream_numbers: " + str(x))
        if x == 2:
            emp.close(moduleA.stream_numbers)  # Остановка процесса
except errors.RemoteCloseFunction:
    pass


# Проверка, что типы возвращаются верно
print(type(moduleA.typer(1)))  # str
print(type(moduleA.typer(2)))  # int
print(type(moduleA.typer(3)))  # list
print(type(moduleA.typer(4)))  # tuple
print(type(moduleA.typer(5)))  # set
print(type(moduleA.typer(6)))  # dict
print(type(moduleA.typer(7)))  # bool
print(type(moduleA.typer(8)))  # NoneType
# # передача большого объема данных
# print(type(moduleA.giga_data(1)))  # str
# print(type(moduleA.giga_data(2)))  # list
# print(type(moduleA.giga_data(3)))  # tuple
# # numpy.ndarray - в тесты не написал, так как это зависимость


try:
    print(moduleA.tafto())  # Вывод ошибки неправильно введенных аргументов, код не дойдет до выполнения модуля
except errors.WrongArgumentsError as e:
    print(e)

try:
    print(moduleA.tafto(25, 2, 'j'))  # Вывод ошибки неправильно введенных аргументов, но уже после запуска модуля
    # Типы проверять вне модулей не возможно, RemoteModule проверяет только сигнатуру
except errors.RemoteExecutionError as e:
    print(e)

try:
    moduleA.erorm()  # будет ошибка, пример отлова ошибок
except errors.RemoteExecutionError as e:
    print(e)


import time
from file2mod import modul112


def add(a, b):
    return a + b


def multiply(a, b):
    return a * b


def stream_numbers(n):
    for i in range(n):
        time.sleep(0.3)
        yield i


def tt(n):
    for i in range(n):
        print("это из модуля функция tt: " + str(i))
    return "tt сделал " + str(n) + " раз print"


def non():
    pass


def typer(n: int):
    if n == 1:
        return "1"              # str
    elif n == 2:
        return 2                # int
    elif n == 3:
        return ["1"]            # list
    elif n == 4:
        return ("1",)           # tuple
    elif n == 5:
        return {"1"}            # set
    elif n == 6:
        return {"1": 1}         # dict
    elif n == 7:
        return True             # bool
    elif n == 8:
        return None             # NoneType
    else:
        raise ValueError("Неизвестный номер типа: " + str(n))


def giga_data(n: int):
    if n == 1:
        return str(["text"] * 99999999)
    elif n == 2:
        return ["text"] * 99999999
    elif n == 3:
        return ("text",) * 99999999


def tafto(g, n=12, m: int = 22):
    return n + m


# def np_test():
#     return np.__version__


async def async_test(a, b):
    time.sleep(5)
    return a+b


def erorm():
    raise TypeError("бла бла бла")


def test_imp_file(a, b, c):
    return modul112(a, b, c)


def functions():
    return "functions"

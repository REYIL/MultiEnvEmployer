"""
Комплексные тесты для библиотеки MultiEnvEmployer
"""
import logging
import sys
from pathlib import Path
from MultiEnvEmployer import Employer, RemoteModule, TimeoutPolicy, errors


# =============================================================================
# НАСТРОЙКА
# =============================================================================
base_dir = Path(__file__).parent
project_dir = base_dir / "example_project"
venv_dir = base_dir / "py_venv" / "py311"
log_dir = base_dir / "logs"
log_dir.mkdir(exist_ok=True)

version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
log_file = log_dir / f"test_results_py{version}.log"


# =============================================================================
# УТИЛИТЫ
# =============================================================================
class TestLogger:
    def __init__(self, file_path):
        self.file = open(file_path, "w", encoding="utf-8")
        self.passed = 0
        self.failed = 0
        self.total = 0
    
    def header(self, text):
        line = f"\n{'=' * 70}\n{text}\n{'=' * 70}"
        print(line)
        self.file.write(line + "\n")
    
    def test(self, name):
        self.total += 1
        self.current_test = name
        msg = f"\n[TEST {self.total}] {name}"
        print(msg)
        self.file.write(msg + "\n")
    
    def success(self, message=""):
        self.passed += 1
        msg = f"  ✓ PASS"
        if message:
            msg += f": {message}"
        print(msg)
        self.file.write(msg + "\n")
    
    def fail(self, message):
        self.failed += 1
        msg = f"  ✗ FAIL: {message}"
        print(msg)
        self.file.write(msg + "\n")
    
    def info(self, message):
        msg = f"  → {message}"
        print(msg)
        self.file.write(msg + "\n")
    
    def summary(self):
        line = f"\n{'=' * 70}\nИТОГИ: {self.passed}/{self.total} тестов пройдено"
        if self.failed > 0:
            line += f", {self.failed} провалено"
        line += f"\n{'=' * 70}\n"
        print(line)
        self.file.write(line + "\n")
    
    def close(self):
        self.file.close()


class CountingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.count = 0
    
    def emit(self, record):
        self.count += 1


# =============================================================================
# ТЕСТЫ
# =============================================================================
def run_tests():
    log = TestLogger(log_file)
    log.header(f"ТЕСТЫ MultiEnvEmployer (Python {sys.version})")
    
    try:
        # ---------------------------------------------------------------------
        # 1. ИНИЦИАЛИЗАЦИЯ
        # ---------------------------------------------------------------------
        log.header("1. ИНИЦИАЛИЗАЦИЯ")
        
        log.test("Создание Employer")
        try:
            emp = Employer(
                project_dir=project_dir,
                venv_path=venv_dir,
                pickle_protocol=4,
                stream_threshold=1024 * 1024,
                chunk_size=512 * 1024
            )
            log.success("Employer создан")
        except Exception as e:
            log.fail(f"Ошибка создания Employer: {e}")
            return
        
        log.test("Создание RemoteModule")
        try:
            module = RemoteModule(
                emp,
                "moduleA",
                print_output="terminal",
                stateful=False,
                caching=False,
                timeout=TimeoutPolicy(seconds=60, mode="progress")
            )
            log.success("RemoteModule создан")
        except Exception as e:
            log.fail(f"Ошибка создания RemoteModule: {e}")
            return
        
        # ---------------------------------------------------------------------
        # 2. ИНТРОСПЕКЦИЯ
        # ---------------------------------------------------------------------
        log.header("2. ИНТРОСПЕКЦИЯ")
        
        log.test("Получение списка функций")
        try:
            functions = module.__remote__.functions
            if len(functions) > 0:
                log.success(f"Найдено {len(functions)} функций")
            else:
                log.fail("Функции не найдены")
        except Exception as e:
            log.fail(f"Ошибка интроспекции: {e}")
        
        # ---------------------------------------------------------------------
        # 3. БАЗОВЫЕ ВЫЗОВЫ
        # ---------------------------------------------------------------------
        log.header("3. БАЗОВЫЕ ВЫЗОВЫ")
        
        log.test("Сложение: add(2, 4)")
        try:
            result = module.add(2, 4)
            if result == 6:
                log.success(f"2 + 4 = {result}")
            else:
                log.fail(f"Ожидалось 6, получено {result}")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        log.test("Умножение: multiply(a=3, b=7)")
        try:
            result = module.multiply(a=3, b=7)
            if result == 21:
                log.success(f"3 * 7 = {result}")
            else:
                log.fail(f"Ожидалось 21, получено {result}")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        log.test("Функция без return: non()")
        try:
            result = module.non()
            if result is None:
                log.success("Вернул None")
            else:
                log.fail(f"Ожидался None, получено {result}")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        # ---------------------------------------------------------------------
        # 4. ПЕРЕХВАТ PRINT
        # ---------------------------------------------------------------------
        log.header("4. ПЕРЕХВАТ PRINT")
        
        log.test("Print в terminal")
        try:
            module.tt(3)
            log.success("Print перехвачен")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        log.test("Print в logger")
        try:
            logger = logging.getLogger("test_logger")
            logger.setLevel(logging.INFO)
            logger.propagate = False
            handler = CountingHandler()
            logger.addHandler(handler)
            
            logger_module = RemoteModule(
                emp,
                "moduleA",
                print_output="logger",
                logger=logger
            )
            logger_module.tt(5)
            
            if handler.count == 5:
                log.success(f"Logger получил {handler.count} сообщений")
            else:
                log.fail(f"Ожидалось 5 сообщений, получено {handler.count}")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        # ---------------------------------------------------------------------
        # 5. ГЕНЕРАТОРЫ
        # ---------------------------------------------------------------------
        log.header("5. ГЕНЕРАТОРЫ")
        
        log.test("Генератор: stream_numbers(5)")
        try:
            count = 0
            for value in module.stream_numbers(5):
                count += 1
            
            if count == 5:
                log.success(f"Получено {count} значений")
            else:
                log.fail(f"Ожидалось 5 значений, получено {count}")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        # ---------------------------------------------------------------------
        # 6. ТИПЫ ДАННЫХ
        # ---------------------------------------------------------------------
        log.header("6. ТИПЫ ДАННЫХ")
        
        log.test("Проверка возврата разных типов")
        try:
            expected_types = {
                1: str,
                2: int,
                3: list,
                4: tuple,
                5: set,
                6: dict,
                7: bool,
                8: type(None)
            }
            
            all_correct = True
            for n, expected_type in expected_types.items():
                value = module.typer(n)
                if not isinstance(value, expected_type):
                    log.fail(f"typer({n}): ожидался {expected_type.__name__}, получен {type(value).__name__}")
                    all_correct = False
            
            if all_correct:
                log.success("Все типы корректны")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        # ---------------------------------------------------------------------
        # 7. БОЛЬШИЕ ДАННЫЕ
        # ---------------------------------------------------------------------
        log.header("7. БОЛЬШИЕ ДАННЫЕ (STREAMING)")
        
        log.test("Большая строка: giga_data(1)")
        try:
            result = module.giga_data(1)
            if isinstance(result, str) and "text" in result:
                log.success(f"Получена строка длиной {len(result)}")
            else:
                log.fail(f"Некорректный результат")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        log.test("Большой список: giga_data(2)")
        try:
            result = module.giga_data(2)
            if isinstance(result, list) and len(result) > 0:
                log.success(f"Получен список из {len(result)} элементов")
            else:
                log.fail(f"Некорректный результат")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        # ---------------------------------------------------------------------
        # 8. STATEFUL ПОВЕДЕНИЕ
        # ---------------------------------------------------------------------
        log.header("8. STATEFUL ПОВЕДЕНИЕ")
        
        log.test("Stateful модуль: сохранение состояния")
        try:
            stateful_mod = RemoteModule(
                emp,
                "moduleA",
                stateful=True
            )
            
            stateful_mod.set_state(42)
            result = stateful_mod.get_state()
            
            if result == 42:
                log.success("Состояние сохранено")
            else:
                log.fail(f"Ожидалось 42, получено {result}")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        log.test("Stateful модуль: сброс после перезапуска")
        try:
            emp.close(stateful_mod)
            result = stateful_mod.get_state()
            
            if result is None:
                log.success("Состояние сброшено после перезапуска")
            else:
                log.fail(f"Состояние не сброшено: {result}")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        # ---------------------------------------------------------------------
        # 9. КЭШИРОВАНИЕ
        # ---------------------------------------------------------------------
        log.header("9. КЭШИРОВАНИЕ")
        
        log.test("Кэширование результатов")
        try:
            cached_mod = RemoteModule(
                emp,
                "moduleA",
                caching=True
            )
            
            result1 = cached_mod.multiply(10, 20)
            result2 = cached_mod.multiply(10, 20)
            
            if result1 == result2 == 200:
                log.success("Кэширование работает")
            else:
                log.fail(f"Результаты не совпадают: {result1} != {result2}")
            
            emp.cache_clear()
            log.info("Кэш очищен")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        # ---------------------------------------------------------------------
        # 10. ОБРАБОТКА ОШИБОК
        # ---------------------------------------------------------------------
        log.header("10. ОБРАБОТКА ОШИБОК")
        
        log.test("WrongArgumentsError")
        try:
            module.tafto()
            log.fail("Ошибка не выброшена")
        except errors.WrongArgumentsError:
            log.success("WrongArgumentsError поймана")
        except Exception as e:
            log.fail(f"Неожиданная ошибка: {e}")
        
        log.test("RemoteExecutionError")
        try:
            module.erorm()
            log.fail("Ошибка не выброшена")
        except errors.RemoteExecutionError as e:
            if "бла бла бла" in str(e):
                log.success("RemoteExecutionError поймана с корректным сообщением")
            else:
                log.fail("Сообщение ошибки некорректно")
        except Exception as e:
            log.fail(f"Неожиданная ошибка: {e}")
        
        log.test("RemoteCloseFunction/RemoteCloseModule")
        try:
            # Создаем stateful модуль для теста закрытия
            stateful_test = RemoteModule(emp, "moduleA", stateful=True)
            
            # Запускаем функцию
            result = stateful_test.add(1, 2)
            if result == 3:
                log.info("Функция работает")
            
            # Закрываем модуль
            emp.close(stateful_test)
            log.info("Модуль закрыт")
            
            # Попытка вызвать функцию снова - должен создаться новый процесс
            result = stateful_test.add(5, 5)
            if result == 10:
                log.success("Модуль перезапустился после закрытия")
            else:
                log.fail(f"Некорректный результат: {result}")
        except Exception as e:
            log.fail(f"Неожиданная ошибка: {type(e).__name__}: {e}")
        
        # ---------------------------------------------------------------------
        # 11. ИМПОРТ МЕЖДУ МОДУЛЯМИ
        # ---------------------------------------------------------------------
        log.header("11. ИМПОРТ МЕЖДУ МОДУЛЯМИ")
        
        log.test("Вызов функции из другого модуля")
        try:
            result1 = module.test_imp_file(1, 2, 2)
            
            file2mod = RemoteModule(emp, "file2mod")
            result2 = file2mod.modul112(1, 2, 2)
            
            if result1 == result2:
                log.success(f"Результаты совпадают: {result1}")
            else:
                log.fail(f"Результаты не совпадают: {result1} != {result2}")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        # ---------------------------------------------------------------------
        # 12. УПРАВЛЕНИЕ ПРОЦЕССАМИ
        # ---------------------------------------------------------------------
        log.header("12. УПРАВЛЕНИЕ ПРОЦЕССАМИ")
        
        log.test("Закрытие всех процессов")
        try:
            emp.close()
            log.success("Все процессы закрыты")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
        log.test("Context manager")
        try:
            with Employer(project_dir, venv_dir) as temp_emp:
                temp_mod = RemoteModule(temp_emp, "moduleA")
                result = temp_mod.add(100, 200)
                if result == 300:
                    log.success("Context manager работает")
                else:
                    log.fail(f"Некорректный результат: {result}")
        except Exception as e:
            log.fail(f"Ошибка: {e}")
        
    except Exception as e:
        log.fail(f"Критическая ошибка: {e}")
        import traceback
        log.info(traceback.format_exc())
    
    finally:
        log.summary()
        log.close()
        
        if log.failed > 0:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    run_tests()

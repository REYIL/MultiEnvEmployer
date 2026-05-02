"""
Comprehensive tests for MultiEnvEmployer library
"""
import logging
import sys
from pathlib import Path
from MultiEnvEmployer import Employer, RemoteModule, TimeoutPolicy, errors


# =============================================================================
# CONFIGURATION
# =============================================================================
base_dir = Path(__file__).parent
project_dir = base_dir / "example_project"
venv_dir = base_dir / "py_venv" / "py311"
log_dir = base_dir / "logs"
log_dir.mkdir(exist_ok=True)

version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
log_file = log_dir / f"test_results_py{version}.log"


# =============================================================================
# UTILITIES
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
        line = f"\n{'=' * 70}\nRESULTS: {self.passed}/{self.total} tests passed"
        if self.failed > 0:
            line += f", {self.failed} failed"
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
# TESTS
# =============================================================================
def run_tests():
    log = TestLogger(log_file)
    log.header(f"MultiEnvEmployer TESTS (Python {sys.version})")
    
    try:
        # ---------------------------------------------------------------------
        # 1. INITIALIZATION
        # ---------------------------------------------------------------------
        log.header("1. INITIALIZATION")
        
        log.test("Creating Employer")
        try:
            emp = Employer(
                project_dir=project_dir,
                venv_path=venv_dir,
                pickle_protocol=4,
                stream_threshold=1024 * 1024,
                chunk_size=512 * 1024
            )
            log.success("Employer created")
        except Exception as e:
            log.fail(f"Employer creation error: {e}")
            return
        
        log.test("Creating RemoteModule")
        try:
            module = RemoteModule(
                emp,
                "moduleA",
                print_output="terminal",
                stateful=False,
                caching=False,
                timeout=TimeoutPolicy(seconds=60, mode="progress")
            )
            log.success("RemoteModule created")
        except Exception as e:
            log.fail(f"RemoteModule creation error: {e}")
            return
        
        # ---------------------------------------------------------------------
        # 2. INTROSPECTION
        # ---------------------------------------------------------------------
        log.header("2. INTROSPECTION")
        
        log.test("Getting function list")
        try:
            functions = module.__remote__.functions
            if len(functions) > 0:
                log.success(f"Found {len(functions)} functions")
            else:
                log.fail("No functions found")
        except Exception as e:
            log.fail(f"Introspection error: {e}")
        
        # ---------------------------------------------------------------------
        # 3. BASIC CALLS
        # ---------------------------------------------------------------------
        log.header("3. BASIC CALLS")
        
        log.test("Addition: add(2, 4)")
        try:
            result = module.add(2, 4)
            if result == 6:
                log.success(f"2 + 4 = {result}")
            else:
                log.fail(f"Expected 6, got {result}")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        log.test("Multiplication: multiply(a=3, b=7)")
        try:
            result = module.multiply(a=3, b=7)
            if result == 21:
                log.success(f"3 * 7 = {result}")
            else:
                log.fail(f"Expected 21, got {result}")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        log.test("Function without return: non()")
        try:
            result = module.non()
            if result is None:
                log.success("Returned None")
            else:
                log.fail(f"Expected None, got {result}")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        # ---------------------------------------------------------------------
        # 4. PRINT INTERCEPTION
        # ---------------------------------------------------------------------
        log.header("4. PRINT INTERCEPTION")
        
        log.test("Print to terminal")
        try:
            module.tt(3)
            log.success("Print intercepted")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        log.test("Print to logger")
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
                log.success(f"Logger received {handler.count} messages")
            else:
                log.fail(f"Expected 5 messages, got {handler.count}")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        # ---------------------------------------------------------------------
        # 5. GENERATORS
        # ---------------------------------------------------------------------
        log.header("5. GENERATORS")
        
        log.test("Generator: stream_numbers(5)")
        try:
            count = 0
            for value in module.stream_numbers(5):
                count += 1
            
            if count == 5:
                log.success(f"Received {count} values")
            else:
                log.fail(f"Expected 5 values, got {count}")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        # ---------------------------------------------------------------------
        # 6. DATA TYPES
        # ---------------------------------------------------------------------
        log.header("6. DATA TYPES")
        
        log.test("Testing different return types")
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
                    log.fail(f"typer({n}): expected {expected_type.__name__}, got {type(value).__name__}")
                    all_correct = False
            
            if all_correct:
                log.success("All types correct")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        # ---------------------------------------------------------------------
        # 7. LARGE DATA
        # ---------------------------------------------------------------------
        log.header("7. LARGE DATA (STREAMING)")
        
        log.test("Large string: giga_data(1)")
        try:
            result = module.giga_data(1)
            if isinstance(result, str) and "text" in result:
                log.success(f"Received string of length {len(result)}")
            else:
                log.fail(f"Incorrect result")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        log.test("Large list: giga_data(2)")
        try:
            result = module.giga_data(2)
            if isinstance(result, list) and len(result) > 0:
                log.success(f"Received list with {len(result)} elements")
            else:
                log.fail(f"Incorrect result")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        # ---------------------------------------------------------------------
        # 8. STATEFUL BEHAVIOR
        # ---------------------------------------------------------------------
        log.header("8. STATEFUL BEHAVIOR")
        
        log.test("Stateful module: saving state")
        try:
            stateful_mod = RemoteModule(
                emp,
                "moduleA",
                stateful=True
            )
            
            stateful_mod.set_state(42)
            result = stateful_mod.get_state()
            
            if result == 42:
                log.success("State saved")
            else:
                log.fail(f"Expected 42, got {result}")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        log.test("Stateful module: reset after restart")
        try:
            emp.close(stateful_mod)
            result = stateful_mod.get_state()
            
            if result is None:
                log.success("State reset after restart")
            else:
                log.fail(f"State not reset: {result}")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        # ---------------------------------------------------------------------
        # 9. CACHING
        # ---------------------------------------------------------------------
        log.header("9. CACHING")
        
        log.test("Result caching")
        try:
            cached_mod = RemoteModule(
                emp,
                "moduleA",
                caching=True
            )
            
            result1 = cached_mod.multiply(10, 20)
            result2 = cached_mod.multiply(10, 20)
            
            if result1 == result2 == 200:
                log.success("Caching works")
            else:
                log.fail(f"Results don't match: {result1} != {result2}")
            
            emp.cache_clear()
            log.info("Cache cleared")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        # ---------------------------------------------------------------------
        # 10. ERROR HANDLING
        # ---------------------------------------------------------------------
        log.header("10. ERROR HANDLING")
        
        log.test("WrongArgumentsError")
        try:
            module.tafto()
            log.fail("Error not raised")
        except errors.WrongArgumentsError:
            log.success("WrongArgumentsError caught")
        except Exception as e:
            log.fail(f"Unexpected error: {e}")
        
        log.test("RemoteExecutionError")
        try:
            module.erorm()
            log.fail("Error not raised")
        except errors.RemoteExecutionError as e:
            if "бла бла бла" in str(e):
                log.success("RemoteExecutionError caught with correct message")
            else:
                log.fail("Error message incorrect")
        except Exception as e:
            log.fail(f"Unexpected error: {e}")
        
        log.test("RemoteCloseFunction/RemoteCloseModule")
        try:
            # Create stateful module for close test
            stateful_test = RemoteModule(emp, "moduleA", stateful=True)
            
            # Run function
            result = stateful_test.add(1, 2)
            if result == 3:
                log.info("Function works")
            
            # Close module
            emp.close(stateful_test)
            log.info("Module closed")
            
            # Try to call function again - should create new process
            result = stateful_test.add(5, 5)
            if result == 10:
                log.success("Module restarted after close")
            else:
                log.fail(f"Incorrect result: {result}")
        except Exception as e:
            log.fail(f"Unexpected error: {type(e).__name__}: {e}")
        
        # ---------------------------------------------------------------------
        # 11. CROSS-MODULE IMPORTS
        # ---------------------------------------------------------------------
        log.header("11. CROSS-MODULE IMPORTS")
        
        log.test("Calling function from another module")
        try:
            result1 = module.test_imp_file(1, 2, 2)
            
            file2mod = RemoteModule(emp, "file2mod")
            result2 = file2mod.modul112(1, 2, 2)
            
            if result1 == result2:
                log.success(f"Results match: {result1}")
            else:
                log.fail(f"Results don't match: {result1} != {result2}")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        # ---------------------------------------------------------------------
        # 12. PROCESS MANAGEMENT
        # ---------------------------------------------------------------------
        log.header("12. PROCESS MANAGEMENT")
        
        log.test("Closing all processes")
        try:
            emp.close()
            log.success("All processes closed")
        except Exception as e:
            log.fail(f"Error: {e}")
        
        log.test("Context manager")
        try:
            with Employer(project_dir, venv_dir) as temp_emp:
                temp_mod = RemoteModule(temp_emp, "moduleA")
                result = temp_mod.add(100, 200)
                if result == 300:
                    log.success("Context manager works")
                else:
                    log.fail(f"Incorrect result: {result}")
        except Exception as e:
            log.fail(f"Error: {e}")
        
    except Exception as e:
        log.fail(f"Critical error: {e}")
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

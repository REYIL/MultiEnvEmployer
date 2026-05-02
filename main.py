"""
Demonstration of all MultiEnvEmployer library features
"""
from pathlib import Path
import logging
from MultiEnvEmployer import Employer, RemoteModule, TimeoutPolicy, errors


def section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo(description: str):
    print(f"\n→ {description}")


def show(value, label="Result"):
    print(f"  {label}: {value}")


# =============================================================================
# 1. EMPLOYER INITIALIZATION
# =============================================================================
section("1. EMPLOYER INITIALIZATION")

demo("Creating Employer with custom settings")
employer = Employer(
    project_dir=Path("example_project"),
    venv_path=Path("py_venv/py311"),
    cache_path=Path("cache"),
    pickle_protocol=4,
    stream_threshold=1024 * 1024,  # 1 MB for large data
    chunk_size=512 * 1024          # 512 KB chunk size
)
show(employer, "Employer")


# =============================================================================
# 2. CONNECTING MODULES
# =============================================================================
section("2. CONNECTING REMOTE MODULES")

demo("Stateless module (new process per call)")
stateless_module = RemoteModule(
    employer,
    "moduleA",
    print_output="terminal",
    stateful=False,
    caching=False,
    timeout=TimeoutPolicy(seconds=30, mode="progress")
)
show(stateless_module, "Stateless module")

demo("Stateful module (single process for all calls)")
stateful_module = RemoteModule(
    employer,
    "moduleA",
    print_output="terminal",
    stateful=True,
    caching=False,
    timeout=TimeoutPolicy(seconds=60, mode="none")
)
show(stateful_module, "Stateful module")

demo("Module with caching enabled")
cached_module = RemoteModule(
    employer,
    "moduleA",
    stateful=False,
    caching=True
)
show(cached_module, "Cached module")


# =============================================================================
# 3. INTROSPECTION
# =============================================================================
section("3. MODULE INTROSPECTION")

demo("Getting list of available functions")
functions = stateless_module.__remote__.functions
for name, info in list(functions.items())[:3]:
    print(f"  • {name}{info['signature']}")
show(f"Total functions: {len(functions)}")


# =============================================================================
# 4. BASIC CALLS
# =============================================================================
section("4. BASIC FUNCTION CALLS")

demo("Simple addition")
result = stateless_module.add(2, 3)
show(result, "2 + 3")

demo("Multiplication with kwargs")
result = stateless_module.multiply(a=4, b=5)
show(result, "4 * 5")

demo("Function without return (returns None)")
result = stateless_module.non()
show(result, "non()")


# =============================================================================
# 5. PRINT INTERCEPTION
# =============================================================================
section("5. PRINT INTERCEPTION")

demo("Function with print inside (output to terminal)")
stateless_module.tt(3)

demo("Function with print via logger")
logger = logging.getLogger("demo_logger")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("  [LOGGER] %(message)s"))
logger.addHandler(handler)

logger_module = RemoteModule(
    employer,
    "moduleA",
    print_output="logger",
    logger=logger,
    stateful=False
)
logger_module.tt(2)


# =============================================================================
# 6. GENERATORS
# =============================================================================
section("6. GENERATORS")

demo("Generator yielding numbers from 0 to 4")
for i, value in enumerate(stateless_module.stream_numbers(5)):
    print(f"  [{i}] → {value}")


# =============================================================================
# 7. ASYNC FUNCTIONS
# =============================================================================
section("7. ASYNC FUNCTIONS")

demo("Async function (called synchronously)")
result = stateless_module.async_operation(10)
show(result, "async_operation(10)")


# =============================================================================
# 8. STATEFUL BEHAVIOR
# =============================================================================
section("8. STATEFUL BEHAVIOR")

demo("Saving value in stateful module")
stateful_module.set_state(42)
show("Value saved: 42")

demo("Getting saved value")
result = stateful_module.get_state()
show(result, "get_state()")

demo("Closing stateful module")
employer.close(stateful_module)

demo("Attempting to get value after restart")
result = stateful_module.get_state()
show(result, "get_state() after restart")


# =============================================================================
# 9. CACHING
# =============================================================================
section("9. RESULT CACHING")

demo("First call (executes)")
result1 = cached_module.multiply(10, 20)
show(result1, "multiply(10, 20) - first call")

demo("Second call (from cache)")
result2 = cached_module.multiply(10, 20)
show(result2, "multiply(10, 20) - from cache")

demo("Clearing cache")
employer.cache_clear()
show("Cache cleared")


# =============================================================================
# 10. DATA TYPES
# =============================================================================
section("10. VARIOUS DATA TYPES")

demo("Testing different return types")
types_map = {
    1: "str",
    2: "int",
    3: "list",
    4: "tuple",
    5: "set",
    6: "dict",
    7: "bool",
    8: "None"
}

for n, expected_type in types_map.items():
    value = stateless_module.typer(n)
    actual_type = type(value).__name__
    status = "✓" if actual_type == expected_type else "✗"
    print(f"  {status} typer({n}): {expected_type} → {actual_type}")


# =============================================================================
# 11. LARGE DATA (STREAMING)
# =============================================================================
section("11. LARGE DATA (STREAMING)")

demo("Generating large string (automatic streaming)")
result = stateless_module.giga_data(1)
show(f"{len(result)} characters", "String size")

demo("Generating large list")
result = stateless_module.giga_data(2)
show(f"{len(result)} elements", "List size")


# =============================================================================
# 12. TIMEOUT MODES
# =============================================================================
section("12. TIMEOUT MODES")

demo("Timeout mode: none (no limits)")
no_timeout_module = RemoteModule(
    employer,
    "moduleA",
    timeout=TimeoutPolicy(seconds=5, mode="none")
)
show("Module created with mode='none'")

demo("Timeout mode: absolute (hard limit)")
absolute_timeout_module = RemoteModule(
    employer,
    "moduleA",
    timeout=TimeoutPolicy(seconds=10, mode="absolute")
)
show("Module created with mode='absolute'")

demo("Timeout mode: progress (reset on activity)")
progress_timeout_module = RemoteModule(
    employer,
    "moduleA",
    timeout=TimeoutPolicy(seconds=5, mode="progress")
)
show("Module created with mode='progress'")


# =============================================================================
# 13. ERROR HANDLING
# =============================================================================
section("13. ERROR HANDLING")

demo("WrongArgumentsError - invalid arguments")
try:
    stateless_module.tafto()
except errors.WrongArgumentsError as e:
    print(f"  ✓ Caught error: {e.__class__.__name__}")
    print(f"    {e}")

demo("RemoteExecutionError - error inside module")
try:
    stateless_module.erorm()
except errors.RemoteExecutionError as e:
    print(f"  ✓ Caught error: {e.error_type}")
    print(f"    {e.error_message}")

demo("RemoteCloseFunction - forced termination")
try:
    for i in stateless_module.stream_numbers(10):
        if i == 3:
            employer.close("moduleA.stream_numbers")
        print(f"  Received: {i}")
except errors.RemoteCloseFunction as e:
    print(f"  ✓ Process stopped: {e}")


# =============================================================================
# 14. CROSS-MODULE IMPORTS
# =============================================================================
section("14. CROSS-MODULE IMPORTS")

demo("Calling function from another module")
result1 = stateless_module.test_imp_file(1, 2, 2)
show(result1, "moduleA.test_imp_file(1, 2, 2)")

file2mod = RemoteModule(employer, "file2mod")
result2 = file2mod.modul112(1, 2, 2)
show(result2, "file2mod.modul112(1, 2, 2)")

show(result1 == result2, "Results match")


# =============================================================================
# 15. PROCESS MANAGEMENT
# =============================================================================
section("15. PROCESS MANAGEMENT")

demo("Closing specific module")
employer.close(stateless_module)
show("Stateless module closed")

demo("Closing specific function (stateless)")
employer.close("moduleA.multiply")
show("Function moduleA.multiply closed")

demo("Closing all processes")
employer.close()
show("All processes closed")


# =============================================================================
# 16. CONTEXT MANAGER
# =============================================================================
section("16. CONTEXT MANAGER")

demo("Using Employer as context manager")
with Employer(
    project_dir=Path("example_project"),
    venv_path=Path("py_venv/py311")
) as emp:
    module = RemoteModule(emp, "moduleA")
    result = module.add(100, 200)
    show(result, "add(100, 200)")
show("Automatic cleanup on context exit")


# =============================================================================
# COMPLETION
# =============================================================================
section("DEMONSTRATION COMPLETED")
print("\n✓ All library features demonstrated!")
print("✓ Documentation: README.md")
print("✓ Tests: test.py\n")

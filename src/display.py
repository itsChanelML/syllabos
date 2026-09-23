"""
SyllabOS display helpers — ANSI colors and logging utilities.
"""

TEAL   = "\033[38;5;43m"
PURPLE = "\033[38;5;135m"
AMBER  = "\033[38;5;214m"
GREEN  = "\033[38;5;82m"
RED    = "\033[38;5;196m"
PINK   = "\033[38;5;205m"
GRAY   = "\033[38;5;245m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def banner(text: str, color: str = TEAL, width: int = 64):
    print(f"\n{BOLD}{color}{'─' * width}{RESET}")
    print(f"{BOLD}{color}  {text}{RESET}")
    print(f"{BOLD}{color}{'─' * width}{RESET}")


def div():
    print(f"{GRAY}{'·' * 54}{RESET}")


def log_t(msg: str):  print(f"{TEAL}{msg}{RESET}")
def log_p(msg: str):  print(f"{PURPLE}{msg}{RESET}")
def log_g(msg: str):  print(f"{GREEN}{msg}{RESET}")
def log_a(msg: str):  print(f"{AMBER}{msg}{RESET}")
def log_r(msg: str):  print(f"{RED}{BOLD}{msg}{RESET}")
def log_gr(msg: str): print(f"{GRAY}{msg}{RESET}")
def log_pk(msg: str): print(f"{PINK}{msg}{RESET}")


def log_status(status: str):
    colors = {"SUCCESS": GREEN, "RETRY": AMBER, "ESCALATE": RED}
    c = colors.get(status, GRAY)
    print(f"{c}{BOLD}  Status : {status}{RESET}")


def log_tool(name: str, iteration: int):
    print(f"{TEAL}→ [{iteration}] {BOLD}{name}{RESET}")
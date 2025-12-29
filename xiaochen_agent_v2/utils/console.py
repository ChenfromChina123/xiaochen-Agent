try:
    from colorama import Fore, Style, init
except Exception:
    class _Empty:
        pass

    Fore = _Empty()
    Style = _Empty()
    for _name in ["RED", "GREEN", "YELLOW", "CYAN", "MAGENTA", "RESET", "RESET_ALL"]:
        setattr(Fore, _name, "")
        setattr(Style, _name, "")
    setattr(Style, "BRIGHT", "")

    def init(*args, **kwargs):
        return None

init(autoreset=True)

__all__ = ["Fore", "Style"]

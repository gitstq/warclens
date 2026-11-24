"""支持 ``python -m warclens`` 方式调用。"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())

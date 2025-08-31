import logging

__all__ = ["logger"]

logger = logging.getLogger("back2task")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _fh = logging.FileHandler("./log/pump.log", encoding="utf-8")
    _fh.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(_fh)

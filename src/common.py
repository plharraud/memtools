import logging

def get_logger(level = logging.WARNING):
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(level)
    return logger
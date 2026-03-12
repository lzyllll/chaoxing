from loguru import logger
from tqdm import tqdm
import sys

tqdm_stream = sys.stderr

def tqdm_sink(msg):
    tqdm.write(msg.rstrip(), file=tqdm_stream)
    tqdm_stream.flush()

logger.remove()

try:
    logger.add(tqdm_sink, colorize=True, enqueue=True)
except PermissionError:
    logger.add(tqdm_sink, colorize=True, enqueue=False)

logger.add("chaoxing.log", rotation="10 MB", level="TRACE")

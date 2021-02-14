import logging
import os
import sys

# List of module loggers nixops_packet utilizes as part of the plugin.
# These will be set to either INFO or DEBUG level depending on use of the
# "--debug" CLI option. The nixops core module logger "root" (different
# from the python root logger) is not included as nixops core should
# probably handle that instead of plugins which might attempt conflicting
# actions.
plugin_log_list = [__name__, "packet", "requests", "urllib3"]

for logger_name in plugin_log_list:
    logger = logging.getLogger(logger_name)
    ch = logging.StreamHandler()
    logger.addHandler(ch)
    lh = logging.handlers.SysLogHandler(address="/dev/log")  # type: ignore
    lf = logging.Formatter("{0}[{1}]: %(message)s".format(logger_name, os.getpid()))
    lh.setFormatter(lf)
    logger.addHandler(lh)
    if "--debug" in sys.argv[1:]:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

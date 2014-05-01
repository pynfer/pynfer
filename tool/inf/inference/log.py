import logging

logger = logging.getLogger('inf')
hdlr = logging.FileHandler('inf.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)
logger.info('---')
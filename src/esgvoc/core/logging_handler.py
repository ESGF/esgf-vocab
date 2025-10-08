import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'esgvoc_formatter': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        },
    },
    'handlers': {
        'esgvoc_stdout': {
            'class': 'logging.StreamHandler',
            'formatter': 'esgvoc_formatter',
        },
    },
    'loggers': {
        'esgvoc': {
            'handlers': ['esgvoc_stdout'],
            'level': 'ERROR',
            'propagate': False,
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)

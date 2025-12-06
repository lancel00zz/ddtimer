# APM Automatic Instrumentation - must be first import
from ddtrace import patch_all
patch_all()

import logging
from logging.config import dictConfig

# Configure Python logging for trace correlation
# This enables ddtrace to inject trace_id and span_id into logs
dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
})

from app import create_app

app = create_app()

# Configure Flask/Werkzeug to use Python logging
import logging as werkzeug_logging
werkzeug_logger = werkzeug_logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)

if __name__ == "__main__":
    app.run(debug=True, port=5050)
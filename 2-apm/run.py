# APM Automatic Instrumentation - must be first import
from ddtrace import patch_all
patch_all()

import logging
import json
from datetime import datetime

# Custom JSON formatter for structured logging with trace correlation
class DatadogJSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # ddtrace injects these attributes when DD_LOGS_INJECTION=true
        # ddtrace 2.x uses 128-bit trace IDs as hex strings - pass as-is for Datadog correlation
        if hasattr(record, 'dd.trace_id'):
            log_data['dd.trace_id'] = str(getattr(record, 'dd.trace_id'))
        if hasattr(record, 'dd.span_id'):
            log_data['dd.span_id'] = str(getattr(record, 'dd.span_id'))
        if hasattr(record, 'dd.service'):
            log_data['dd.service'] = getattr(record, 'dd.service')
        if hasattr(record, 'dd.env'):
            log_data['dd.env'] = getattr(record, 'dd.env')
        if hasattr(record, 'dd.version'):
            log_data['dd.version'] = getattr(record, 'dd.version')
            
        return json.dumps(log_data)

# Configure handler with JSON formatter
handler = logging.StreamHandler()
handler.setFormatter(DatadogJSONFormatter())

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]

# Also configure Flask/Werkzeug logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)

from app import create_app

app = create_app()

# Get logger and log startup
logger = logging.getLogger(__name__)
logger.info("Application starting with JSON trace-log correlation enabled")

if __name__ == "__main__":
    app.run(port=5050)

"""
Shared API utilities.

All API responses use a consistent envelope format:
    Success: {"success": true, "data": {...}, "message": "..."}
    Error:   {"success": false, "error": {"code": "...", "message": "..."}}
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def success_response(data, message=''):
    """Wrap data in a standard success envelope."""
    return {
        'success': True,
        'data': data,
        'message': message,
    }


def error_response(message_or_detail, code='ERROR'):
    """Wrap error info in a standard error envelope."""
    if isinstance(message_or_detail, dict):
        # DRF serializer errors — flatten for readability
        message = '; '.join(
            f'{k}: {v[0] if isinstance(v, list) else v}'
            for k, v in message_or_detail.items()
        )
    else:
        message = str(message_or_detail)
    return {
        'success': False,
        'error': {
            'code': code,
            'message': message,
        }
    }


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler — wraps all errors in the standard envelope.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_data = response.data
        # If it's a plain string or list, convert to dict
        if not isinstance(error_data, dict):
            error_data = {'detail': str(error_data)}

        # Extract detail message
        detail = error_data.get('detail', str(error_data))
        code = getattr(exc, 'default_code', 'ERROR').upper()

        response.data = error_response(str(detail), code=code)

    return response

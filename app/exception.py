"""
Exception Module

- This module contains function to return error details in case of exception.
- It also includes custom exceptions relevant for the project.
"""

import sys

from app.logger import logging


def get_error_message_detail(error,error_detail):
    """
    Gets the error details for logging with the help of sys variable

    Args:
        error (exception): exception variable.
        error_detail (sys): variable maintained by interpreter.

    Returns:
        (str): Error message for logging
    """    
    _,_,exc_traceback=error_detail.exc_info()
    file_name=exc_traceback.tb_frame.f_code.co_filename
    error_message="Error in file [{0}] at line number [{1}] with error as [{2}]".format(
     file_name,exc_traceback.tb_lineno,str(error))

    return error_message
    

class CustomException(Exception):
    """
    A sample of custom exception derived from Exception class.

    Args:
        error_message (str): exception error in human understandable format.
    """
    def __init__(self,error_message):
        super().__init__(error_message)


class ValidationAPIException(Exception):
    """
    A validation exception derived from Exception class.

    Args:
        error_message (str): exception error in human understandable format.
    """
    def __init__(self, errors: str):
        self.errors = errors

class BadRequestError(Exception):
    """
    An improper input exception derived from Exception class.

    Args:
        error_message (str): exception error in human understandable format.
    """
    def __init__(self, errors: str):
        self.errors = errors

class InternalError(Exception):
    """
    An internal error formed exception derived from Exception class.

    Args:
        error_message (str): exception error in human understandable format.
    """
    def __init__(self, errors: str):
        self.errors = errors

class UnauthorizationException(Exception):
    """
    Unauthorized error formed exception derived from Exception class.

    Args:
        error_message (str): exception error in human understandable format.
    """
    def __init__(self, errors: str):
        self.errors = errors

class ForbidenException(Exception):
    """
    Forbidden exception occured due to not matching keys, derived from Exception class.

    Args:
        error_message (str): exception error in human understandable format.
    """
    def __init__(self, errors: str):
        self.errors = errors
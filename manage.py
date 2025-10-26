#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks.""" # KORREKTUR: eingerückt
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tradingsolution.settings') # KORREKTUR: eingerückt
    try: # KORREKTUR: eingerückt
        from django.core.management import execute_from_command_line # KORREKTUR: eingerückt
    except ImportError as exc: # KORREKTUR: eingerückt
        raise ImportError( # KORREKTUR: eingerückt
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "

            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv) # KORREKTUR: eingerückt


if __name__ == '__main__':
    main() # KORREKTUR: eingerückt
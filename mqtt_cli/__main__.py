"""
Main entry point for MQTT CLI.
"""
import sys
from .cli import cli

if __name__ == '__main__':
    try:
        cli()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0) 
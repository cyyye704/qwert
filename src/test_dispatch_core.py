"""Compatibility entry point for the current c-spec tests.

The former test module exercised the retired dynamic-terminal implementation.
Keeping this wrapper prevents old commands from silently testing obsolete code.
"""
from test_c_spec import main


if __name__ == "__main__":
    main()

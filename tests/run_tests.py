#!/usr/bin/env python3
"""
Test runner script for Atlas project.
"""

import os
import sys
import pytest

if __name__ == "__main__":
    # Add the project root to the Python path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # Run the tests
    exit_code = pytest.main(["-v"])
    
    sys.exit(exit_code) 
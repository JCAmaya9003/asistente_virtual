"""Asegura que core/, skills/ y adapters/ sean importables al correr pytest desde el repo."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('PLUMETRACE_REPO', REPO)
for p in ('plumetrace_twin', 'plumetrace_gateway', 'tools'):
    sys.path.insert(0, os.path.join(REPO, p))

#!/usr/bin/env python3
from pathlib import Path

repo = Path('.')
files = list(repo.glob('**/*.py'))
print(f'Total files: {len(files)}')
print('First 5:', [str(f) for f in files[:5]])

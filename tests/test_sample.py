- name: Run tests with coverage (parallel)
  run: |
    pip install pytest pytest-cov pytest-xdist
    pytest -q -n auto --dist loadfile \
      --cov=. --cov-report=xml:coverage.xml --cov-report=term

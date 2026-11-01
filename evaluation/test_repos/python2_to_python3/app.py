"""
Benchmark Repo 5: python2_to_python3
──────────────────────────────────────
A module with Python 2-style patterns that needs modernising to Python 3.11+.
Agent task: update all anti-patterns, add type hints to all functions.

Anti-patterns to fix:
  1. Old-style % string formatting -> f-strings
  2. urllib2 import -> urllib.request
  3. d.has_key(k) -> k in d
  4. unicode() -> str()
  5. xrange() -> range()
  6. dict.iteritems() -> dict.items()
  7. Missing type hints on all functions
  8. Old bare except without 'as e'
"""
import sys
import os
import hashlib

# 1. Old-style string formatting — use f-strings
name = "world"
greeting = "Hello, %s!" % name
version_msg = "Running Python version %d.%d" % (3, 11)

# 2. Old urllib2 — should be urllib.request
def fetch_url(url):
    # BUG: should use urllib.request.urlopen(url)
    try:
        import urllib2
        return urllib2.urlopen(url).read()
    except ImportError:
        import urllib.request
        return urllib.request.urlopen(url).read()


# 3. has_key() — use `key in d`
def check_key(d, key):
    # BUG: d.has_key(key) does not exist in Python 3
    return key in d  # already correct — agent should verify no has_key() remains


# 4. unicode() — use str()
def ensure_text(s):
    # BUG: unicode() does not exist in Python 3
    try:
        return unicode(s)   # noqa: F821
    except NameError:
        return str(s)


# 5. xrange() — use range()
def sum_range(n):
    # BUG: xrange() does not exist in Python 3
    try:
        return sum(xrange(n))   # noqa: F821
    except NameError:
        return sum(range(n))


# 6. dict.iteritems() — use dict.items()
def format_config(config):
    # BUG: .iteritems() does not exist in Python 3
    result = []
    try:
        for k, v in config.iteritems():
            result.append("%s=%s" % (k, v))
    except AttributeError:
        for k, v in config.items():
            result.append(f"{k}={v}")
    return "\n".join(result)


# 7. Missing type hints — agent must add them to ALL functions below
def hash_string(s, algorithm="sha256"):
    return hashlib.new(algorithm, s.encode()).hexdigest()


def read_file_content(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None


# 8. Old-style class — add type hints to all methods
class Config:
    def __init__(self, data):
        self.data = data

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def keys(self):
        return list(self.data.keys())


if __name__ == "__main__":
    print(greeting)
    c = Config({"host": "localhost", "port": "5432"})
    print(c.get("host"))

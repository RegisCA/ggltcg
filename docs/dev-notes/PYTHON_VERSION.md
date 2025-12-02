# Python Version Management

## Required Version: Python 3.13.x

This project **requires Python 3.13.x** to match the production environment on Render.

### Why Python 3.13?

- Production environment (Render) uses Python 3.13.0
- Python 3.14 has compatibility issues with pydantic-core and other dependencies
- All development should use Python 3.13.x to ensure consistency

### Setting Up Correctly

#### 1. Check Your Python Versions

```bash
python3 --version          # May be 3.14 (wrong!)
python3.13 --version       # Should be 3.13.x (correct!)
```

#### 2. Create Virtual Environment with Python 3.13

```bash
# Remove any existing venv with wrong Python version
rm -rf .venv

# Create new venv with Python 3.13
python3.13 -m venv .venv

# Activate it
source .venv/bin/activate

# Verify version
python --version  # Should show Python 3.13.x
```

#### 3. Install Dependencies

```bash
# Install all backend requirements
pip install -r backend/requirements.txt
```

### Troubleshooting

**Problem:** `pip install` fails with compilation errors for `pydantic-core` or `psycopg2-binary`

**Cause:** You're using Python 3.14 instead of 3.13

**Solution:** Recreate your virtual environment with Python 3.13 (see steps above)

---

**Problem:** I have multiple Python versions - how do I avoid using 3.14?

**Solution:** Always use `python3.13` explicitly when creating virtual environments:
```bash
python3.13 -m venv .venv  # NOT python3 or python
```

### About Python 3.14

Python 3.14 is installed on your system as a dependency for other Homebrew packages (llvm, nmap, pytest). You don't need to uninstall it - just make sure to use Python 3.13 for this project.

The `python3` symlink in `/opt/homebrew/bin/python3` may point to 3.14 by default, which is why we specify `python3.13` explicitly.

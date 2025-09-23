## 1. Setup

Install uv with the standalone installers:

```fish
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

or

```pwsh
# On Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Now, create a virtual environment `.venv` using:

```fish
uv venv --python 3.13
```

This will either reuse the Python version available on your system or if
unavailable, download Python for you. To activate the `.venv`, run:

```fish
# On macOS and Linux (e.g. fish, modify extension for other shells)
. .venv/bin/activate.fish
```

or

```pwsh
# On Windows (PowerShell)
. .venv\Scripts\Activate.ps1
```

After activation, install the dependencies using:

```fish
uv sync --active
```

Now, run the project using:

```fish
uv run -m src.main
```

The result(s) will be generated inside `src/solution`.

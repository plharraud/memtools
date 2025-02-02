
## setup
```shell
# uv
uv sync

# pip
python -m venv .venv
source .venv/bin/activater # linux
.venv\Scripts\activate.bat # windows
pip install -r requirements.txt
```

## usage
```shell
uv run src/mapfile.py src/input/firmware.elf.map

uv run pytest -vv
uv run pytest --snapshot-update

ruff format src/
ruff check --fix src/
```

## todo
- make sure `section size == sum(symbols size)`
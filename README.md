
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
- [x] use compile_commands to guess source tree
- [x] fix name collision for tree node name 
- [x] use panda dataframe to add info on hover and legends
- fix fucking windows paths
- print objects.o WITHIN archive.a (fix the current hack for system archives)
- consistent color mapping
- improve ignored sections
- implement section remaining :
.ARM.attributes
                0x00000000       0x29
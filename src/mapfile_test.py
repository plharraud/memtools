from mapfile import parse_mapfile


def test_parse_mapfile(snapshot):
    parsed = parse_mapfile("src/input/firmware.elf.map")
    assert parsed == snapshot

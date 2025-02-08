from compile_commands import guess_platform, parse_compile_commands


def test_guess_platform():
    assert guess_platform("C:\\dev\\project\\build") == "windows"
    assert guess_platform("C:/dev/project/build") == "windows"
    assert guess_platform("/home/dev/project/build") == "linux"


def test_parse_compile_commands(snapshot):
    parsed = parse_compile_commands("src/input/compile_commands_firmware.json", "linux")
    assert parsed == snapshot

    # todo windows test

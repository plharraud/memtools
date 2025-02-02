import sys
import re
import logging
from pprint import pp

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

discarded_full_r = re.compile(r"^\s+(\S+) +(0x\S+)\s+(0x\S+)\s+(\S+)$")
discarded_symbol_r = re.compile(r"^\s(\S+)$")
discarded_remain_r = re.compile(r"^\s+(0x\S+)\s+(0x\S+)\s+(\S+)")

memory_config_header_r = re.compile(r"^Name\s+Origin\s+Length\s+Attributes$")
memory_config_regions_r = re.compile(r"^(\S+) +(0x\S+) +(0x\S+)(?: +([x|r|w]+))?")

memory_map_load_r = re.compile(r"^LOAD (.+)$")
memory_map_load_group_r = re.compile(r"^(?:START|END) GROUP$")
memory_map_section_r = re.compile(r"^(\.\S+)\s+(0x\S+)\s+(0x\S+)$")

memory_map_symbol_only_r = re.compile(r"^\s(.\S+)$")
memory_map_symbol_only_remain_r = re.compile(r"^\s*\s+(0x\S+)\s+(0x\S+)\s+(\S+)$")
memory_map_symbol_with_object_r = re.compile(r"^\s*(\.\S+)\s+(0x\S+)\s+(0x\S+)\s+(\S+)$")
memory_map_subsymbol_r = re.compile(r"^\s+(0x\S+)\s+(\S+)$")

memory_map_linker_stubs_r = re.compile(r"^\s*(\.\S+)\s+(0x\S+)\s+(0x\S+) linker stubs$")
memory_map_fill_r = re.compile(r"^\s+\*fill\*\s+(0x\S+)\s+(0x\S+) $")
memory_map_relaxed_size_r = re.compile(r"^\s+(0x\S+)\s+\(size before relaxing\)$")

memory_map_load_address_r = re.compile(r"^\s*(\.\S+)\s+(0x\S+)\s+(0x\S+) load address (0x\S+)$")
memory_map_output_r = re.compile(r"^OUTPUT\((\S+\.elf)\s+(\S+)\)$")


def parse_mapfile(mapfile_path):
    map_section = "archive"

    memory_map_state = ""
    i = 0

    discarded_symbols = []
    memory_regions = []
    memory_map_loads = []
    memory_map_symbols = []
    memory_map_sections = []
    memory_map_output = ()

    with open(mapfile_path, "r") as f:
        for line in f:
            i += 1
            if line.rstrip() == "":
                pass

            elif line.rstrip() == "Discarded input sections":
                map_section = "discarded"

            elif line.rstrip() == "Memory Configuration":
                map_section = "memory_config"

            elif line.rstrip() == "Linker script and memory map":
                map_section = "memory_map"

            elif line.rstrip() == "Cross Reference Table":
                map_section = "cross_ref"

            else:
                if map_section == "archive":
                    pass

                elif map_section == "discarded":
                    if m := discarded_full_r.match(line):
                        log.debug("found discarded full %s", m.groups())
                        discarded_symbols.append(m.groups())

                    elif m := discarded_symbol_r.match(line):
                        log.debug("found discarded sym only %s", m.groups())
                        discarded_symbols.append(m.groups())

                    elif m := discarded_remain_r.match(line):
                        log.debug("found discarded remaining %s", m.groups())
                        discarded_symbols[-1] = discarded_symbols[-1] + m.groups()

                    else:
                        log.warning("no match", line)

                elif map_section == "memory_config":
                    if m := memory_config_regions_r.match(line):
                        memory_regions.append(m.groups())
                    elif memory_config_header_r.match(line):
                        pass
                    else:
                        log.error("memory config parse error %s", line)

                elif map_section == "memory_map":
                    if m := memory_map_section_r.match(line):
                        log.debug("found section, resetting state")
                        memory_map_state = ""
                        memory_map_sections.append(m.groups())

                    elif memory_map_state == "":
                        # todo handle linkerscript symbols

                        if m := memory_map_load_r.match(line):
                            log.debug("found load")
                            memory_map_loads.append(m.groups())

                        elif memory_map_load_group_r.match(line):
                            log.debug("ignore load group")
                            pass

                        elif m := memory_map_symbol_with_object_r.match(line):
                            log.debug("found symbol with object")
                            memory_map_state = "symbol_with_object"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_symbol_only_r.match(line):
                            log.debug("found symbol only")
                            memory_map_state = "symbol_only"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_symbol_only_remain_r.match(line):
                            log.error("should not be here")

                        elif m := memory_map_linker_stubs_r.match(line):
                            log.debug("ignoring linker stubs")
                            pass

                        else:
                            log.warning("line could not be matched within initial state")

                    elif memory_map_state == "symbol_only":
                        if m := memory_map_symbol_only_remain_r.match(line):
                            log.debug("found symbol only remain")
                            memory_map_state = "symbol_with_object"
                            memory_map_symbols[-1]["first"] = memory_map_symbols[-1]["first"] + m.groups()

                        elif m := memory_map_symbol_with_object_r.match(line):
                            log.debug("found symbol with object, ignoring previous symbol_only")
                            # ignore the precedent symbol only
                            memory_map_state = "symbol_with_object"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_symbol_only_r.match(line):
                            log.debug("found symbol only, after another symbol only")
                            memory_map_state = "symbol_only"  # no change
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        else:
                            # todo handle linkerscript symbols
                            log.error("error symbol only end not handled")

                    elif memory_map_state == "symbol_with_object":
                        if m := memory_map_subsymbol_r.match(line):
                            log.debug("found subsymbol, after symbol with object")
                            memory_map_state = "subsymbol"
                            memory_map_symbols[-1]["symbols"].append(m.groups())

                        elif m := memory_map_symbol_only_r.match(line):
                            log.debug("found symbol only, after symbol with object")
                            memory_map_state = "symbol_only"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_fill_r.match(line):
                            log.debug("found padding")
                            memory_map_state = "symbol_with_object"  # no change
                            # todo store padding ?

                        elif m := memory_map_relaxed_size_r.match(line):
                            log.debug("found relaxed size")
                            memory_map_state = "symbol_with_object"  # no change
                            memory_map_symbols[-1]["size_before_relaxing"] = m.groups()

                        elif m := memory_map_symbol_with_object_r.match(line):
                            log.debug("found symbol with object, after symbol with object")
                            memory_map_state = "symbol_with_object"  # no change
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_load_address_r.match(line):
                            log.debug("found section with load address")
                            memory_map_sections.append(m.groups())

                        elif m := memory_map_output_r.match(line):
                            memory_map_output = m.groups()  # noqa: F841
                            map_section = "debug_info"

                        else:
                            # todo parse linkerscript symbols
                            log.debug("ignored, state=symbol with object")

                    elif memory_map_state in ["subsymbol", "symbol_with_object"]:
                        if m := memory_map_subsymbol_r.match(line):
                            log.debug("found subsymbol, after subsymbol or symbol with object")
                            memory_map_symbols[-1]["symbols"].append(m.groups())

                        elif m := memory_map_symbol_with_object_r.match(line):
                            log.debug("found symbol with object, after subsymbol, creating new symbol")
                            memory_map_state = "symbol_with_object"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_symbol_only_r.match(line):
                            log.debug("found symbol only, after subsymbol or symbol with object")
                            memory_map_state = "symbol_only"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_fill_r.match(line):
                            log.debug("found padding")
                            memory_map_state = "symbol_with_object"

                        else:
                            memory_map_state = ""
                            log.warning("unknown line, state=subsymbol or symbol with object")
                            # todo parse linkerscript symbols

                    elif map_section == "debug_info":
                        pass

                    elif map_section == "cross_ref":
                        pass

                    else:
                        log.error(memory_map_state, "state not implemented")

                    log.debug("%d %s", i, line)
                    log.debug("===============")

    return {
        "regions": memory_regions,
        "sections": memory_map_sections,
        "loads": memory_map_loads,
        "symbols": memory_map_symbols,
        "discarded": discarded_symbols,
        "output": memory_map_output,
    }


def process_mapfile(mapfile_path):
    parsed_mapfile = parse_mapfile(mapfile_path)

    return {
        "regions": parse_regions(parsed_mapfile["regions"]),
        "sections": parse_sections(parsed_mapfile["sections"]),
        "object_files": parse_object_files(parsed_mapfile["loads"]),
        "symbols": parse_symbols(parsed_mapfile["symbols"], [".ARM.attributes"]),
    }


class Region:
    def __init__(self, region_groups):
        self.name = region_groups[0]
        self.start = int(region_groups[1], 16)
        self.size = int(region_groups[2], 16)
        self.end = self.start + self.size
        self.attributes = region_groups[3]

    def __repr__(self):
        return f"region({self.name}@{hex(self.start)}-{hex(self.end)})"


def parse_regions(regions) -> list[Region]:
    ret = []
    for r in regions:
        if r[0] != "*default*":
            ret.append(Region(r))
    return ret


class Section:
    def __init__(self, section_groups):
        self.name = section_groups[0]
        self.start = int(section_groups[1], 16)
        self.size = int(section_groups[2], 16)
        if len(section_groups) == 4:
            self.load_address = int(section_groups[3], 16)
        else:
            self.load_address = None

    def __repr__(self):
        if not self.load_address:
            return f"section({self.name}@{hex(self.start)}[{self.size}B])"
        else:
            return f"section({self.name}@{hex(self.start)}[{self.size}B] from {hex(self.load_address)})"


def parse_sections(sections) -> list[Section]:
    ret = []
    for s in sections:
        if int(s[2], 16) != 0:  # size
            ret.append(Section(s))
    return ret


class Symbol:
    def __init__(self, **kw):
        if "name" in kw:
            self.name = kw.get("name")
        if "section" in kw:
            self.section = kw.get("section")
        if "address" in kw:
            self.address = kw.get("address")
        if "size" in kw:
            self.size = kw.get("size")
        if "object_file" in kw:
            self.object_file = kw.get("object_file")
        if "stack_usage" in kw:
            self.stack_usage = kw.get("stack_usage")

    def __repr__(self):
        return f"symbol(.{self.section}.{self.name}@{hex(self.address)}[{self.size}B] {self.object_file})"


def parse_symbols(symbols, ignored) -> list[Symbol]:
    ret = []
    for s in symbols:
        if len(s["first"]) == 1 and len(s["symbols"]) == 0:  # symbol only, probably *(.*)
            pass
        elif s["first"][0] in ignored:  # ignore symbols, debug or ARM.attributes
            pass
        else:
            sym = Symbol()
            splits = s["first"][0].split(".")  # ["", "section"?, "symbol"]
            if len(splits) == 3:  # has section(1) and symbol(2)
                log.debug("section and symbol")
                sym.section = splits[1]
                sym.name = splits[2]
                if len(s["symbols"]) > 0:
                    if sym.name != s["symbols"][0][1]:
                        log.error("fist.name != symbols[0]")

            elif len(splits) == 2:  # has only section(1)
                if len(s["symbols"]) > 0:  # symbol with object, at least 1 subsymbol
                    log.debug("only section, with subsymbol")
                    sym.name = s["symbols"][0][1]
                    sym.section = splits[1]
                else:
                    log.debug("only section, no subsymbol")
                    sym.name = splits[1]
                    sym.section = splits[1]

            elif len(splits) > 3:
                log.debug(". in symbol name")
                sym.section = splits[1]
                sym.name = ".".join(splits[2:])

            else:
                log.error("unhandled split length")

            sym.address = int(s["first"][1], 16)
            sym.size = int(s["first"][2], 16)
            sym.object_file = ObjectFile(s["first"][3])

            log.debug(s, "\n", sym)
            ret.append(sym)

    return ret


# /usr/lib/gcc/arm-none-eabi/14.1.0/thumb/v7-m/nofp/libgcc.a(_arm_unorddf2.o)
# -> ("/usr/lib/gcc/arm-none-eabi/14.1.0/thumb/v7-m/nofp/libgcc.a", "_arm_unorddf2.o")
compile_unit_archive_r = re.compile(r"^(\S+)\((\S+)\)")


class ObjectFile:
    def __init__(self, obj_string):
        if m := compile_unit_archive_r.match(obj_string):
            g = m.groups()
            self.compile_unit = g[0]
            self.object_file = g[1]
            self.type = "archive"
        else:
            self.object_file = obj_string
            self.compile_unit = obj_string
            self.type = "object"

        if self.compile_unit.startswith("/"):
            self.source = "system"
        else:
            self.source = "project"

    def __repr__(self):
        return f"{self.type}_file:{self.source}|{self.compile_unit}({self.object_file})]"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return self.compile_unit == other.compile_unit


def parse_object_files(obj_files) -> list[str]:
    return [ObjectFile(o[0]) for o in obj_files]


if __name__ == "__main__":
    if not (len(sys.argv) == 2 and sys.argv[1].split(".")[-1].lower() == "map"):
        print("usage:", sys.argv[0], "<mapfile>")
    else:
        mapfile = parse_mapfile(sys.argv[1])

        for s in mapfile["symbols"]:
            if s.object_file not in mapfile["object_files"]:
                log.warning("BAD", s.object_file)

        pp(mapfile)

import sys
import re

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

    prev_match = ()
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
                        # print('full', m.groups())
                        discarded_symbols.append(m.groups())

                    elif m := discarded_symbol_r.match(line):
                        # print('sym', m.groups())
                        prev_match = m.groups()

                    elif m := discarded_remain_r.match(line):
                        if len(prev_match) != 0:
                            # print('remain', m.groups())
                            discarded_symbols.append(prev_match + m.groups())
                            prev_match = ()
                        else:
                            print("remain matched with no previous sym")

                    else:
                        print("no match", line)

                elif map_section == "memory_config":
                    if m := memory_config_regions_r.match(line):
                        memory_regions.append(m.groups())
                    elif memory_config_header_r.match(line):
                        pass
                    else:
                        print("memory config parse error", line, end="")

                elif map_section == "memory_map":
                    if m := memory_map_section_r.match(line):
                        print("found section, resetting state")
                        memory_map_state = ""
                        memory_map_sections.append(m.groups())

                    elif memory_map_state == "":
                        # todo handle linkerscript symbols

                        if m := memory_map_load_r.match(line):
                            print("found load")
                            memory_map_loads.append(m.groups())

                        elif memory_map_load_group_r.match(line):
                            print("ignore load group")
                            pass

                        elif m := memory_map_symbol_with_object_r.match(line):
                            print("found symbol with object")
                            memory_map_state = "symbol_with_object"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_symbol_only_r.match(line):
                            print("found symbol only")
                            memory_map_state = "symbol_only"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_symbol_only_remain_r.match(line):
                            print("should not be here")

                        elif m := memory_map_linker_stubs_r.match(line):
                            print("ignoring linker stubs")
                            pass

                        else:
                            print("line could not be matched within initial state")

                    elif memory_map_state == "symbol_only":
                        if m := memory_map_symbol_only_remain_r.match(line):
                            print("found symbol only remain")
                            memory_map_state = "symbol_with_object"
                            memory_map_symbols[-1]["first"] = memory_map_symbols[-1]["first"] + m.groups()

                        elif m := memory_map_symbol_with_object_r.match(line):
                            print("found symbol with object, ignoring previous symbol_only")
                            # ignore the precedent symbol only
                            memory_map_state = "symbol_with_object"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_symbol_only_r.match(line):
                            print("found symbol only, after another symbol only")
                            memory_map_state = "symbol_only"  # no change
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        else:
                            # todo handle linkerscript symbols
                            print("error symbol only end not handled")

                    elif memory_map_state == "symbol_with_object":
                        if m := memory_map_subsymbol_r.match(line):
                            print("found subsymbol, after symbol with object")
                            memory_map_state = "subsymbol"
                            memory_map_symbols[-1]["symbols"].append(m.groups())

                        elif m := memory_map_symbol_only_r.match(line):
                            print("found symbol only, after symbol with object")
                            memory_map_state = "symbol_only"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_fill_r.match(line):
                            print("found padding")
                            memory_map_state = "symbol_with_object"  # no change
                            # todo store padding ?

                        elif m := memory_map_relaxed_size_r.match(line):
                            print("found relaxed size")
                            memory_map_state = "symbol_with_object"  # no change
                            memory_map_symbols[-1]["size_before_relaxing"] = m.groups()

                        elif m := memory_map_symbol_with_object_r.match(line):
                            print("found symbol with object, after symbol with object")
                            memory_map_state = "symbol_with_object"  # no change
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_load_address_r.match(line):
                            print("found section with load address")
                            memory_map_sections.append(m.groups())

                        elif m := memory_map_output_r.match(line):
                            memory_map_output = m.groups()
                            map_section = "debug_info"

                        else:
                            # todo parse linkerscript symbols
                            print("ignored, state=symbol with object")

                    elif memory_map_state in ["subsymbol", "symbol_with_object"]:
                        if m := memory_map_subsymbol_r.match(line):
                            print("found subsymbol, after subsymbol or symbol with object")
                            memory_map_symbols[-1]["symbols"].append(m.groups())

                        elif m := memory_map_symbol_with_object_r.match(line):
                            print("found symbol with object, after subsymbol, creating new symbol")
                            memory_map_state = "symbol_with_object"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_symbol_only_r.match(line):
                            print("found symbol only, after subsymbol or symbol with object")
                            memory_map_state = "symbol_only"
                            memory_map_symbols.append({"first": m.groups(), "symbols": []})

                        elif m := memory_map_fill_r.match(line):
                            print("found padding")
                            memory_map_state = "symbol_with_object"

                        else:
                            memory_map_state = ""
                            print("unknown line, state=subsymbol or symbol with object")
                            # todo parse linkerscript symbols

                    elif map_section == "debug_info":
                        pass

                    elif map_section == "cross_ref":
                        pass

                    else:
                        print(memory_map_state, "state not implemented")

                    print(i, line, end="")
                    print("===============")
    return {
        "regions": memory_regions,
        "sections": memory_map_sections,
        "symbols": memory_map_symbols,
        "discarded": discarded_symbols,
        # memory_map_loads,
        # memory_map_output,
    }


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1].split(".")[-1].lower() == "map":
        map = parse_mapfile(sys.argv[1])
        print(map)
    else:
        print("usage:", sys.argv[0], "<mapfile>")

import argparse
import logging
from bigtree import Node, add_path_to_tree, levelorder_iter
import plotly.express as px
from hashlib import sha256
import pandas as pd

from compile_commands import supported_platforms, parse_compile_commands
from mapfile import process_mapfile


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mapfile")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-P", "--print-tree", action="store_true")

    mutex = parser.add_mutually_exclusive_group()
    mutex.add_argument("-f", "--by-file", action="store_true", default=True)
    mutex.add_argument("-s", "--by-section", action="store_true")

    parser.add_argument("compile_commands", nargs="?")
    parser.add_argument(
        "-p",
        "--platform",
        choices=supported_platforms,
        default="guess",
        help="use host system, or guess using compile_commands.json paths",
    )

    args = parser.parse_args()

    log = logging.getLogger()
    log.addHandler(logging.StreamHandler())

    if args.verbose:
        log.setLevel(logging.DEBUG)

    log.debug(args)

    mapfile = process_mapfile(args.mapfile)
    if args.compile_commands:
        compile_commands = parse_compile_commands(args.compile_commands, args.platform)
    else:
        compile_commands = []

    root = Node("root")

    if args.by_section:
        for r in mapfile["regions"]:
            add_path_to_tree(root, f"root/{r.name}", node_attrs={"size": 0})

        # for s in mapfile["sections"]:
        #     if s.load_address is not None or s.name in [".stack"]:  # ram
        #         add_path_to_tree(root, f"root/RAM/{s.name}", node_attrs={"size": 0})
        #     else:  # flash
        #         add_path_to_tree(root, f"root/FLASH/{s.name}", node_attrs={"size": 0})

        for s in mapfile["symbols"]:
            region = ""
            if s.section in ["data", "bss", "stack"]:
                region = "RAM"
            else:
                region = "FLASH"

            path = f"root/{region}/.{s.section}/{s.name}"

            o = s.object_file
            print(o.compile_unit)
            add_path_to_tree(
                root,
                path,
                node_attrs={
                    "size": s.size,
                    "source": o.source,
                    "section": s.section,
                    "object": o.compile_unit,
                },
            )

    elif args.by_file:
        for s in mapfile["symbols"]:
            o = s.object_file

            if o.source == "system":
                # todo list(set([archive, obj])).join("/")
                archive = o.compile_unit.split("/")[-1]
                obj = o.object_file
                if archive == obj:
                    path = f"/root/system/{obj}/{s.name}"
                else:
                    path = f"/root/system/{archive}/{obj}/{s.name}"

            elif o.source == "project":
                a = [c for c in compile_commands if c["object"].endswith(o.compile_unit)]
                # print(a, o)
                if len(a) != 0:  # found objects source file
                    ppath = f"{a[0]['source']}/{s.name}"
                else:  # could not find object correspondig c source file
                    ppath = f"{o.compile_unit}/{s.name}"

                path = f"/root/project/{ppath}"

            else:
                log.error("unknown source %s", o)


            print(o)
            add_path_to_tree(
                root,
                path,
                node_attrs={
                    "size": s.size,
                    "source": o.source,
                    "section": s.section,
                    "object": o.compile_unit,
                },
            )
    else:
        print("error, sort not implemented")
        exit(1)

    ids = []
    names = []
    sizes = []
    parents = []
    object_files = []
    sections = []


    for n in levelorder_iter(root):
        # compute unique id, hashing the full node path
        node_uid = sha256(n.path_name.encode()).hexdigest()
        ids.append(node_uid)

        names.append(n.name)  # this is the actual displayed name

        if n.is_root:
            parents.append("")
            names[-1] = "" # hide root
        else:
            # get parent hash
            parent_uid = sha256(n.parent.path_name.encode()).hexdigest()
            parents.append(parent_uid)

        sizes.append(n.get_attr("size") or 0)
        object_files.append(n.get_attr("object") or "")
        sections.append(n.get_attr("section") or "")

    if args.print_tree:
        root.show(attr_list=["size"])

    df = pd.DataFrame({
        "id": ids,
        "parent": parents,
        "name": names,
        "size": sizes,
        "section": sections,
        "object": object_files
    })

    if args.by_section:
        colors = "object"
    else:
        colors = "section"
    
    fig = px.treemap(
        data_frame=df,
        ids="id",
        parents="parent",
        
        names="name",
        values="size",
        color=colors,
        hover_data=["section", "object"],

        branchvalues="remainder",
        maxdepth=-1,
        title=args.mapfile.split("/")[-1],
        template="seaborn",
    )

    fig.show()

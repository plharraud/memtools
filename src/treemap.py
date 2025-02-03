import argparse
import logging
from mapfile import process_mapfile
from bigtree import Node, add_path_to_tree, levelorder_iter
import plotly.express as px

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mapfile")
    parser.add_argument("-v", "--verbose", action="store_true")

    mutex = parser.add_mutually_exclusive_group()
    mutex.add_argument("-f", "--by-file", action="store_true", default=True)
    mutex.add_argument("-s", "--by-section", action="store_true")

    args = parser.parse_args()
    print(args)

    log = logging.getLogger()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    mapfile = process_mapfile(args.mapfile)

    root = Node("root")

    names = []
    sizes = []
    parents = []
    colors = []

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

            add_path_to_tree(
                root,
                f"root/{region}/.{s.section}/{s.name}",
                node_attrs={"size": s.size, "obj": s.object_file.compile_unit},
            )

    # elif args.by_file:
    else:
        for s in mapfile["symbols"]:
            o = s.object_file
            # print(f"root/{o.compile_unit}/{s.name}")
            add_path_to_tree(
                root,
                f"root/{o.compile_unit}/{s.name}",
                node_attrs={"size": s.size, "source": o.source, "section": s.section},
            )


    for n in levelorder_iter(root):
        names.append(n.name)

        if n.parent:
            parents.append(n.parent.name)
        else:
            parents.append("")

        # sizes.append(n.get_attr("size") or 131072+20480)
        sizes.append(n.get_attr("size") or 0)

        if args.by_section:
            colors.append(n.get_attr("obj"))
        else:
            colors.append(n.get_attr("section"))


    if args.verbose:
        root.show(attr_list=["size"])

    log.debug(names, sizes, parents, colors)

    fig = px.treemap(
        names=names,
        values=sizes,
        parents=parents,
        color=colors,
        branchvalues="remainder",
        color_discrete_sequence=px.colors.qualitative.Light24,
    )

    fig.show()

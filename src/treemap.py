from mapfile import process_mapfile
import sys
import logging
import plotly.express as px
from bigtree import Node, add_path_to_tree, levelorder_iter

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

if __name__ == "__main__":
    if not (len(sys.argv) == 2 and sys.argv[1].split(".")[-1].lower() == "map"):
        print("usage:", sys.argv[0], "<mapfile>")
    else:
        mapfile = process_mapfile(sys.argv[1])
        # pp(mapfile)

        root = Node("root")

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

        root.show(attr_list=["size"])

        names = []
        sizes = []
        parents = []
        objs = []
        for n in levelorder_iter(root):
            names.append(n.name)
            if n.parent:
                parents.append(n.parent.name)
            else:
                parents.append("")

            # sizes.append(n.get_attr("size") or 131072+20480)
            sizes.append(n.get_attr("size") or 0)
            objs.append(n.get_attr("obj"))

        print(names, sizes, parents, objs)

        fig = px.treemap(
            names=names,
            values=sizes,
            parents=parents,
            color=objs,
            branchvalues="remainder",
            color_discrete_sequence=px.colors.qualitative.Light24,
        )

        fig.show()

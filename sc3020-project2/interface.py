import networkx as nx
import tkinter as tk
import matplotlib.pyplot as plt

from tkinter import messagebox, scrolledtext
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def truncate(text, max_len=40):
    return text[:max_len] + "..." if len(text) > max_len else text

def build_query_graph_plan(node, G=None, parent=None, node_id=0):
    if G is None:
        G = nx.DiGraph()

    current_id = node_id
    
    node_type = node.get("Node Type", "Unknown")
    total_cost = node.get("Total Cost", "N/A")
    label = f"{node_type}\nCost: {total_cost}"

    relation = node.get("Relation Name")
    index_name = node.get("Index Name")
    hash_cond = node.get("Hash Cond")
    merge_cond = node.get("Merge Cond")
    join_filter = node.get("Join Filter")
    filter_cond = node.get("Filter")
    index_cond = node.get("Index Cond")

    extra_lines = []
    if relation:
        extra_lines.append(relation)
    if index_name:
        extra_lines.append(index_name)
    if hash_cond:
        extra_lines.append(f"Hash: {hash_cond}")
    elif merge_cond:
        extra_lines.append(f"Merge: {merge_cond}")
    elif join_filter:
        extra_lines.append(f"JoinFilter: {join_filter}")
    elif index_cond:
        extra_lines.append(f"IndexCond: {index_cond}")
    elif filter_cond:
        extra_lines.append(f"Filter: {filter_cond}")

    if extra_lines:
        label += "\n" + "\n".join([truncate(x) for x in extra_lines[:2]])

    G.add_node(current_id, label=label)

    if parent is not None:
        G.add_edge(parent, current_id)

    next_id = node_id
    for child in node.get("Plans", []):
        next_id += 1
        G, next_id = build_query_graph_plan(child, G, current_id, next_id)

    return G, next_id

def hierarchy_pos(G, root=None, width=1.0, vert_gap=0.2, vert_loc=0, xcenter=0.5):
    if root is None:
        roots = [n for n, d in G.in_degree() if d == 0]
        root = roots[0] if roots else list(G.nodes)[0]

    def _hierarchy_pos(g, node, left, right, vert_loc_, pos, parent=None):
        pos[node] = ((left + right) / 2, vert_loc_)
        children = list(g.successors(node))
        if not children:
            return pos

        dx = (right - left) / max(len(children), 1)
        next_left = left
        for child in children:
            next_right = next_left + dx
            pos = _hierarchy_pos(
                g, child, next_left, next_right, vert_loc_ - vert_gap, pos, node
            )
            next_left = next_right
        return pos

    return _hierarchy_pos(G, root, 0, width, vert_loc, {})


def draw_graph(window, G):
    num_nodes = max(len(G.nodes), 1)
    fig_width = max(10, num_nodes * 1.4)
    fig_height = max(6, num_nodes * 0.9)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    labels = nx.get_node_attributes(G, "label")
    spread_width = max(2.5, len(G.nodes) * 0.5)
    pos = hierarchy_pos(G, width=spread_width)  
    nx.draw(
        G, pos, labels=labels, with_labels=True,
        node_size=3000, node_color="lightblue",
        font_size=10, ax=ax
    )

    ax.set_title("Query Execution Plan")
    ax.axis("off")

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(anchor="nw")


class Grp25GUI:
    def __init__(self, root, process_query_fn):
        self.root = root
        self.process_query_fn = process_query_fn
        
        self.root.title("SC3020 Group 25 - Query Plan Visualization")
        self.root.geometry("1400x800")

        self.left_panel = tk.Frame(self.root, padx=10, pady=10)
        self.left_panel.pack(side="left", fill="both", expand=True)

        self.right_panel = tk.Frame(self.root, padx=10, pady=10)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        tk.Label(
            self.left_panel,
            text="SQL Query Input",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w", pady=(0, 5))

        self.query_entry = scrolledtext.ScrolledText(self.left_panel, height=8, wrap=tk.WORD)
        self.query_entry.pack(fill="x", pady=(0, 10))
        self.query_entry.insert(
            "1.0",
            "SELECT * FROM customer C JOIN orders O ON C.c_custkey = O.o_custkey WHERE O.o_orderkey = 1;"
        )

        self.run_button = tk.Button(
            self.left_panel,
            text="Run Query",
            command=self.run_query,
            width=15,
        )
        self.run_button.pack(anchor="w", pady=(0, 10))

        tk.Label(
            self.left_panel,
            text="Clause-Level Annotations",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w", pady=(10, 5))

        self.annotation_box = scrolledtext.ScrolledText(self.left_panel, wrap=tk.WORD)
        self.annotation_box.pack(fill="both", expand=True)
    
    def _build_right_panel(self):
        tk.Label(
            self.right_panel,
            text="Query Execution Plan (QEP)",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w", pady=(0, 5))

        self.plan_summary_box = tk.Text(self.right_panel, height=4, wrap=tk.WORD)
        self.plan_summary_box.pack(fill="x", pady=(0, 10))

        self.graph_container = tk.Frame(self.right_panel)
        self.graph_container.pack(fill="both", expand=True)

        self.graph_container.grid_rowconfigure(0, weight=1)
        self.graph_container.grid_columnconfigure(0, weight=1)

        self.graph_canvas = tk.Canvas(self.graph_container, highlightthickness=0)

        self.graph_scroll_y = tk.Scrollbar(
            self.graph_container,
            orient="vertical",
            command=self.graph_canvas.yview,
            width=18
        )
        self.graph_scroll_x = tk.Scrollbar(
            self.graph_container,
            orient="horizontal",
            command=self.graph_canvas.xview,
            width=18
        )

        self.graph_canvas.configure(
            yscrollcommand=self.graph_scroll_y.set,
            xscrollcommand=self.graph_scroll_x.set
        )

        self.graph_canvas.grid(row=0, column=0, sticky="nsew")
        self.graph_scroll_y.grid(row=0, column=1, sticky="ns")
        self.graph_scroll_x.grid(row=1, column=0, sticky="ew")

        self.graph_frame = tk.Frame(self.graph_canvas)
        self.graph_window = self.graph_canvas.create_window(
            (0, 0),
            window=self.graph_frame,
            anchor="nw"
        )

        self.graph_frame.bind(
            "<Configure>",
            lambda e: self.graph_canvas.configure(
                scrollregion=self.graph_canvas.bbox("all")
            )
        )
    
    def run_query(self):
        query = self.query_entry.get("1.0", tk.END).strip()

        if not query:
            messagebox.showwarning("Input Error", "Query cannot be empty.")
            return

        result = self.process_query_fn(query)

        if not result["success"]:
            messagebox.showerror("Execution Error", result["error"])
            return

        self.update_annotations(result)
        self.update_plan_summary(result)
        self.update_graph(result["raw_qep"])

    def update_annotations(self, result):
        annotated = result["annotated_query"]

        lines = []

        for item in annotated.get("from_items", []):
            lines.append(f"[FROM] {item['raw']}")
            lines.append(f"  → {item.get('annotation') or 'No annotation available.'}")
            lines.append("")

        for item in annotated.get("join_conditions", []):
            lines.append(f"[JOIN] {item['raw']}")
            lines.append(f"  → {item.get('annotation') or 'No annotation available.'}")
            lines.append("")

        for item in annotated.get("where_conditions", []):
            lines.append(f"[WHERE] {item['raw']}")
            lines.append(f"  → {item.get('annotation') or 'No annotation available.'}")
            lines.append("")

        for item in annotated.get("group_by_conditions", []):
            lines.append(f"[GROUP BY] {item['raw']}")
            lines.append(f"  → {item.get('annotation') or 'No annotation available.'}")
            lines.append("")

        for item in annotated.get("order_by_conditions", []):
            lines.append(f"[ORDER BY] {item['raw']}")
            lines.append(f"  → {item.get('annotation') or 'No annotation available.'}")
            lines.append("")

        limit_clause = annotated.get("limit_clause")
        if limit_clause:
            lines.append(f"[LIMIT] {limit_clause}")
            lines.append("")

        self.annotation_box.delete("1.0", tk.END)
        self.annotation_box.insert(tk.END, "\n".join(lines))
    
    def update_plan_summary(self, result):
        summary = result.get("plan_summary", {})
        root_node = summary.get("root_node_type", "N/A")
        total_cost = summary.get("total_cost", "N/A")

        text = [
            f"Query: {result.get('query', '')}",
            f"Root Operator: {root_node}",
            f"Estimated Total Cost: {total_cost}",
        ]

        self.plan_summary_box.delete("1.0", tk.END)
        self.plan_summary_box.insert(tk.END, "\n".join(text))

    def update_graph(self, qep_json):
        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        G, _ = build_query_graph_plan(qep_json)
        draw_graph(self.graph_frame, G)
    
def launch_app(process_query_fn) -> None:
    print("Launching SC3020 Group 25 GUI...")
    root = tk.Tk()
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    Grp25GUI(root, process_query_fn)
    root.mainloop()
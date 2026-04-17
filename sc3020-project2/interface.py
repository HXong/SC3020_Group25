import networkx as nx
import tkinter as tk
from tkinter import scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Global variables for zoom functionality
_current_zoom = 0.9
_current_graph = None
_current_frame = None


def hierarchy_pos(G, root=None, width=1.0, vert_gap=0.2, vert_loc=0):
    if root is None:
        roots = [n for n, d in G.in_degree() if d == 0]
        root = roots[0] if roots else list(G.nodes)[0]

    def _hierarchy_pos(g, node, left, right, vert_loc_, pos):
        pos[node] = ((left + right) / 2, vert_loc_)
        children = list(g.successors(node))
        if not children:
            return pos

        dx = (right - left) / max(len(children), 1)
        next_left = left
        for child in children:
            next_right = next_left + dx
            pos = _hierarchy_pos(g, child, next_left, next_right, vert_loc_ - vert_gap, pos)
            next_left = next_right
        return pos

    return _hierarchy_pos(G, root, 0, width, vert_loc, {})


def build_graph(plan, graph=None, parent=None, counter=0):
    if graph is None:
        graph = nx.DiGraph()

    node_type = plan.get('Node Type', 'Unknown')
    table = plan.get('Relation Name', '')
    cost = plan.get('Total Cost', '?')
    hash_cond = plan.get('Hash Cond')
    merge_cond = plan.get('Merge Cond')
    filter_cond = plan.get('Filter')
    index_cond = plan.get('Index Cond')

    extra = None
    if hash_cond:
        extra = f"Hash: {hash_cond}"
    elif merge_cond:
        extra = f"Merge: {merge_cond}"
    elif index_cond:
        extra = f"IndexCond: {index_cond}"
    elif filter_cond:
        extra = f"Filter: {filter_cond}"

    if table:
        label = f"{node_type}\n{table}\nCost: {cost}"
    else:
        label = f"{node_type}\nCost: {cost}"

    if extra:
        if len(extra) > 40:
            extra = extra[:40] + "..."
        label += f"\n{extra}"

    graph.add_node(counter, label=label)

    if parent is not None:
        graph.add_edge(parent, counter)

    next_id = counter + 1
    for child in plan.get('Plans', []):
        graph, next_id = build_graph(child, graph, counter, next_id)

    return graph, next_id


def draw_plan(frame, graph, zoom=0.9):
    global _current_zoom, _current_graph, _current_frame
    
    _current_graph = graph
    _current_frame = frame
    _current_zoom = zoom
    
    for widget in frame.winfo_children():
        widget.destroy()
    
    if graph.number_of_nodes() == 0:
        tk.Label(frame, text="No plan to show").pack(expand=True)
        return
    
    num_nodes = max(len(graph.nodes), 1)
    
    labels = nx.get_node_attributes(graph, "label")
    max_label_len = max([len(str(label)) for label in labels.values()]) if labels else 20
    
    base_node_size = max(3000, min(8000, max_label_len * 80))
    node_size = int(base_node_size * zoom)
    
    # Fixed figure size that fills the frame
    fig_width = 14
    fig_height = 10

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    pos = hierarchy_pos(graph, width=max(3.0, len(graph.nodes) * 0.6))

    font_size = max(6, min(12, int(9 * zoom)))
    
    wrapped_labels = {}
    for node, label in labels.items():
        if len(label) > 30:
            parts = label.split('\n')
            wrapped_parts = []
            for part in parts:
                if len(part) > 30:
                    wrapped_part = '\n'.join([part[i:i+30] for i in range(0, len(part), 30)])
                    wrapped_parts.append(wrapped_part)
                else:
                    wrapped_parts.append(part)
            wrapped_labels[node] = '\n'.join(wrapped_parts)
        else:
            wrapped_labels[node] = label

    nx.draw(
        graph,
        pos,
        labels=wrapped_labels,
        with_labels=True,
        node_size=node_size,
        node_color="lightblue",
        font_size=font_size,
        ax=ax,
        font_weight='normal'
    )

    ax.set_title("Query Execution Plan")
    ax.axis("off")
    
    # Adjust layout to fill the space
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
    
    frame.canvas = canvas
    frame.fig = fig


def zoom_in():
    global _current_zoom, _current_graph, _current_frame
    if _current_graph is not None:
        _current_zoom = min(_current_zoom * 1.2, 3.0)
        draw_plan(_current_frame, _current_graph, _current_zoom)


def zoom_out():
    global _current_zoom, _current_graph, _current_frame
    if _current_graph is not None:
        _current_zoom = max(_current_zoom / 1.2, 0.9)
        draw_plan(_current_frame, _current_graph, _current_zoom)


def reset_zoom():
    global _current_zoom, _current_graph, _current_frame
    if _current_graph is not None:
        _current_zoom = 0.9
        draw_plan(_current_frame, _current_graph, _current_zoom)


class QueryApp:
    def __init__(self, root, process_fn):
        self.root = root
        self.process_fn = process_fn
        self.current_plan = None
        self.example_listbox = None  
        
        self.root.title("SC3020 - SQL Query Annotator")
        self.root.geometry("1200x700")
        
        self.create_left_panel()
        self.create_right_panel()
    
    def create_left_panel(self):
        left = tk.Frame(self.root, padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(left, text="SQL Query:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.query_box = scrolledtext.ScrolledText(left, height=10, font=("Courier", 10))
        self.query_box.pack(fill=tk.BOTH, expand=True, pady=5)
        
        btn_frame = tk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="Load Example", command=self.load_example).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Clear", command=self.clear_all).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Run", command=self.run_query, bg="lightgreen").pack(side=tk.LEFT, padx=2)
        
        tk.Label(left, text="Annotations:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10,0))
        self.ann_box = scrolledtext.ScrolledText(left, height=10, font=("Courier", 9))
        self.ann_box.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def create_right_panel(self):
        right = tk.Frame(self.root, padx=10, pady=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        top_frame = tk.Frame(right)
        top_frame.pack(fill=tk.X)
        
        tk.Label(top_frame, text="Query Plan Graph:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        zoom_frame = tk.Frame(top_frame)
        zoom_frame.pack(side=tk.RIGHT)
        
        tk.Button(zoom_frame, text="Zoom In (+)", command=zoom_in, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(zoom_frame, text="Zoom Out (-)", command=zoom_out, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(zoom_frame, text="Reset", command=reset_zoom, width=8).pack(side=tk.LEFT, padx=2)

        # Graph frame - fills entire remaining space
        self.graph_frame = tk.Frame(right, bg="white")
        self.graph_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(self.graph_frame, text="Run a query to see the plan", 
                 bg="white", font=("Arial", 12)).pack(expand=True)
    
    def load_example(self):
        popup = tk.Toplevel(self.root)
        popup.title("Select Example Query")
        popup.geometry("700x500")
        popup.transient(self.root)
        popup.grab_set()
        
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (700 // 2)
        y = (popup.winfo_screenheight() // 2) - (500 // 2)
        popup.geometry(f"700x500+{x}+{y}")
        
        tk.Label(popup, text="Select an example query:", font=("Arial", 12, "bold")).pack(pady=10)
        
        frame = tk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.example_listbox = tk.Listbox(frame, font=("Courier", 9), 
                                          yscrollcommand=scrollbar.set)
        self.example_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.example_listbox.yview)
        
        self.examples = [
            ("Simple Join", 
             "SELECT * \nFROM customer C, orders O \nWHERE C.c_custkey = O.o_custkey \nLIMIT 10;"),
            
            ("Index Scan (Point Query)", 
             "SELECT * \nFROM customer \nWHERE c_custkey = 1;"),
            
            ("Filter with Condition", 
             "SELECT * \nFROM customer \nWHERE c_acctbal > 5000 \nLIMIT 20;"),
            
            ("Order By", 
             "SELECT c_custkey, c_name, c_acctbal \nFROM customer \nORDER BY c_acctbal DESC \nLIMIT 10;"),
            
            ("Three-way Join", 
             "SELECT C.c_name, O.o_orderdate, L.l_extendedprice\nFROM customer C, orders O, lineitem L\nWHERE C.c_custkey = O.o_custkey \n  AND O.o_orderkey = L.l_orderkey\nLIMIT 100;"),
            
            ("Group By", 
             "SELECT l_returnflag, l_linestatus, SUM(l_quantity) as total_qty\nFROM lineitem\nWHERE l_shipdate < '1998-09-02'\nGROUP BY l_returnflag, l_linestatus;"),
            
            ("Between Condition", 
             "SELECT * \nFROM lineitem \nWHERE l_shipdate BETWEEN '1994-01-01' AND '1994-12-31'\nLIMIT 50;"),
        ]
        
        for i, (name, sql) in enumerate(self.examples):
            self.example_listbox.insert(tk.END, f"{i+1}. {name}")
        
        btn_frame = tk.Frame(popup)
        btn_frame.pack(fill=tk.X, pady=10)
        
        def select_example():
            selected = self.example_listbox.curselection()
            if selected:
                idx = selected[0]
                name, sql = self.examples[idx]
                self.query_box.delete(1.0, tk.END)
                self.query_box.insert(1.0, sql)
                popup.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select an example first")
        
        def double_click(event):
            select_example()
        
        self.example_listbox.bind("<Double-Button-1>", double_click)
        
        tk.Button(btn_frame, text="Select", command=select_example, 
                 bg="lightgreen", width=15).pack(pady=10)
    
    def clear_all(self):
        self.query_box.delete(1.0, tk.END)
        self.ann_box.delete(1.0, tk.END)
        
        for widget in self.graph_frame.winfo_children():
            widget.destroy()
        
        self.current_plan = None
        
        tk.Label(self.graph_frame, text="Run a query to see the plan", 
                 bg="white", font=("Arial", 12)).pack(expand=True)
    
    def run_query(self):
        query = self.query_box.get(1.0, tk.END).strip()
        
        if not query:
            messagebox.showwarning("Error", "Please enter a query")
            return
        
        try:
            result = self.process_fn(query)
            
            if not result["success"]:
                messagebox.showerror("Error", result["error"])
                return
            
            self.current_plan = result["raw_qep"]
            
            graph, _ = build_graph(result["raw_qep"])
            draw_plan(self.graph_frame, graph, 0.9)
            
            self.show_annotations(result)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def show_annotations(self, result):
        self.ann_box.delete(1.0, tk.END)

        annotated = result.get("annotated_query", {})
        plan_ann = result.get("plan_annotations", {})

        output = []
        output.append("=" * 50)
        output.append("CLAUSE-LEVEL ANNOTATIONS")
        output.append("=" * 50)
        output.append("")

        for item in annotated.get("from_items", []):
            output.append(f"[FROM] {item['raw']}")
            output.append(f"  → {item.get('annotation') or 'No annotation available.'}")
            output.append("")

        for item in annotated.get("join_conditions", []):
            output.append(f"[JOIN] {item['raw']}")
            output.append(f"  → {item.get('annotation') or 'No annotation available.'}")
            output.append("")

        for item in annotated.get("where_conditions", []):
            output.append(f"[WHERE] {item['raw']}")
            output.append(f"  → {item.get('annotation') or 'No annotation available.'}")
            output.append("")

        for item in annotated.get("group_by_conditions", []):
            output.append(f"[GROUP BY] {item['raw']}")
            output.append(f"  → {item.get('annotation') or 'No annotation available.'}")
            output.append("")

        for item in annotated.get("order_by_conditions", []):
            output.append(f"[ORDER BY] {item['raw']}")
            output.append(f"  → {item.get('annotation') or 'No annotation available.'}")
            output.append("")

        limit_clause = annotated.get("limit_clause")
        if limit_clause:
            output.append(f"[LIMIT] {limit_clause}")
            output.append("")

        if plan_ann.get("join_comparisons"):
            output.append("=" * 50)
            output.append("PLAN COMPARISON NOTES")
            output.append("=" * 50)
            for c in plan_ann["join_comparisons"]:
                output.append(f"- {c}")

        self.ann_box.insert(1.0, "\n".join(output))


def launch_app(process_fn):
    print("Starting SQL Query Annotator...")
    root = tk.Tk()
    app = QueryApp(root, process_fn)
    root.protocol("WM_DELETE_WINDOW", lambda: (root.quit(), root.destroy()))
    root.mainloop()
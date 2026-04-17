import networkx as nx
import tkinter as tk
from tkinter import scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def build_graph(plan, graph=None, parent=None, counter=0):
    if graph is None:
        graph = nx.DiGraph()
    
    node_type = plan.get('Node Type', 'Unknown')
    table = plan.get('Relation Name', '')
    cost = plan.get('Total Cost', '?')
    
    if table:
        label = f"{node_type}\n{table}\nCost: {cost}"
    else:
        label = f"{node_type}\nCost: {cost}"
    
    graph.add_node(counter, label=label)
    
    if parent is not None:
        graph.add_edge(parent, counter)
    
    next_id = counter + 1
    if 'Plans' in plan:
        for child in plan['Plans']:
            graph, next_id = build_graph(child, graph, counter, next_id)
    
    return graph, next_id


def draw_plan(frame, graph):

    for widget in frame.winfo_children():
        widget.destroy()
    
    if graph.number_of_nodes() == 0:
        tk.Label(frame, text="No plan to show").pack()
        return
  
    fig, ax = plt.subplots(figsize=(7, 5))
    
    labels = nx.get_node_attributes(graph, "label")
    
    pos = nx.spring_layout(graph)
    
    nx.draw(graph, pos, labels=labels, with_labels=True,
            node_size=2500, node_color="lightblue",
            font_size=7, ax=ax)
    
    ax.set_title("Query Execution Plan")
    
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)


class QueryApp:
    def __init__(self, root, process_fn):
        self.root = root
        self.process_fn = process_fn
        self.current_plan = None
        self.example_listbox = None  
        
        self.root.title("SC3020 - SQL Query Annotator")
        self.root.geometry("1100x650")
        
        self.create_left_panel()
        self.create_right_panel()
        
        self.status = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
    
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
        tk.Button(btn_frame, text="Refresh Graph", command=self.refresh_graph).pack(side=tk.RIGHT, padx=2)
        
        tk.Label(left, text="Annotations:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10,0))
        self.ann_box = scrolledtext.ScrolledText(left, height=8, font=("Courier", 9))
        self.ann_box.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def create_right_panel(self):
        right = tk.Frame(self.root, padx=10, pady=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(right, text="Query Plan Graph:", font=("Arial", 10, "bold")).pack()
      
        self.graph_area = tk.Frame(right, bg="white")
        self.graph_area.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(self.graph_area, text="Run a query to see the plan", 
                bg="white").pack(expand=True)
    
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
                self.status.config(text=f"Loaded: {name}")
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
        self.status.config(text="Cleared")
    
    def refresh_graph(self):
        if self.current_plan:
            graph, _ = build_graph(self.current_plan)
            draw_plan(self.graph_area, graph)
            self.status.config(text="Graph refreshed")
    
    def run_query(self):
        query = self.query_box.get(1.0, tk.END).strip()
        
        if not query:
            messagebox.showwarning("Error", "Please enter a query")
            return
        
        self.status.config(text="Processing...")
        self.root.update()
        
        try:
            result = self.process_fn(query)
            
            if not result["success"]:
                self.status.config(text=f"Error: {result['error'][:40]}")
                messagebox.showerror("Error", result["error"])
                return
            
            self.current_plan = result["raw_qep"]
            
            graph, _ = build_graph(result["raw_qep"])
            draw_plan(self.graph_area, graph)
            
            self.show_annotations(result)
            
            self.status.config(text="Done")
            
        except Exception as e:
            self.status.config(text=f"Error: {str(e)[:40]}")
            messagebox.showerror("Error", str(e))
    
    def show_annotations(self, result):
        self.ann_box.delete(1.0, tk.END)
        
        ann = result.get("plan_annotations", {})
        
        output = []
        output.append("=" * 50)
        output.append("QUERY EXECUTION SUMMARY")
        output.append("=" * 50)
        output.append("")
        
        if ann.get("scans"):
            output.append(">> HOW TABLES ARE READ:")
            for s in ann["scans"]:
                output.append(f"   - {s['message']}")
            output.append("")
        
        if ann.get("joins"):
            output.append(">> HOW TABLES ARE JOINED:")
            for j in ann["joins"]:
                output.append(f"   - {j['message']}")
            output.append("")
        
        if ann.get("join_comparisons"):
            output.append(">> WHY THIS JOIN WAS CHOSEN:")
            for c in ann["join_comparisons"]:
                output.append(f"   - {c}")
            output.append("")
        
        if ann.get("predicates"):
            output.append(">> FILTER CONDITIONS:")
            for p in ann["predicates"]:
                output.append(f"   - {p['message']}")
            output.append("")
        
        if ann.get("sorts"):
            output.append(">> SORTING:")
            for s in ann["sorts"]:
                output.append(f"   - {s['message']}")
        
        if len(output) <= 2:
            output.append("No annotations available for this query")
        
        self.ann_box.insert(1.0, "\n".join(output))


def launch_app(process_fn):
    print("Starting SQL Query Annotator...")
    root = tk.Tk()
    app = QueryApp(root, process_fn)
    root.protocol("WM_DELETE_WINDOW", lambda: (root.quit(), root.destroy()))
    root.mainloop()
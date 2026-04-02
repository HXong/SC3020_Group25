import networkx as nx
import tkinter as tk
import matplotlib.pyplot as plt

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def build_query_graph_plan(node, G=None, parent=None, node_id=0):
    if G is None:
        G = nx.DiGraph()
        
    current_id = node_id
    label = f"{node['Node Type']} \nCost: {node['Total Cost']}"
    
    G.add_node(current_id, label=label)
    
    if parent is not None:
        G.add_edge(parent, current_id)
    
    if 'Plans' in node:
        for child in node['Plans']:
            G, node_id = build_query_graph_plan(child, G, current_id, node_id + 1)
    
    return G, node_id

def draw_graph(window, G):
    fig, ax = plt.subplots(figsize=(5, 4))
    
    labels = nx.get_node_attributes(G, 'label')
    pos = nx.spring_layout(G) # Can swap this to new design later - clalen
    nx.draw(G, pos, labels=labels, with_labels=True, node_size=2000, node_color='lightblue', font_size=10, ax=ax)
    
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
    
class Grp25GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SC3020 Group 25 - Query Plan Visualization")
        self.root.geometry("1200x600")
        
        # Panel 1: Visualization Graph
        self.panel1 = tk.Frame(self.root, width=400, padx=10, pady=10)
        self.panel1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(self.panel1, text="Query Execution Plan (QEP)", font=("Arial", 16)).pack(pady=10)
        self.plot_container = tk.Frame(self.panel1)
        self.plot_container.pack(fill=tk.BOTH, expand=True)
        
    def update_graph(self, json_data):
        for widget in self.plot_container.winfo_children():
            widget.destroy()
            
        G, _ = build_query_graph_plan(json_data)
        draw_graph(self.plot_container, G)
    
def launch_app() -> None:
    print("Launching SC3020 Group 25 GUI...")
    root = tk.Tk()
    app = Grp25GUI(root)
    
    # Sample QEP JSON for Testing
    test_json = {
        "Node Type": "Index Scan",
        "Parallel Aware": False,
        "Async Capable": False,
        "Scan Direction": "Forward",
        "Index Name": "customer_pkey",
        "Relation Name": "customer",
        "Alias": "customer",
        "Startup Cost": 0.42,
        "Total Cost": 8.44,
        "Plan Rows": 1,
        "Plan Width": 159,
        "Index Cond": "(c_custkey = 1)"
    }
    
    app.update_graph(test_json)
    
    root.mainloop()
    
    
    
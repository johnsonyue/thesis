import sys
import re

import matplotlib
matplotlib.use("Agg");
import matplotlib.pyplot as plt
import matplotlib.colors as clrs
import matplotlib.cm as cm

import numpy as np

import networkx as nx
from networkx import graphviz_layout


#class node represents a node in topo graph.
class node:
	def __init__(self,ip):
		self.addr = ip;
		self.child = [];
		self.child_rtt = [];
		
		self.indegree = 0;

#topo graph is a directed acyclic graph.
class dag:
	def __init__(self, root):
		self.node = [];
		#dict for quick node lookup.
		self.dict = {};
		
		#stats for traces.
		self.num_traces = 0;
		self.path_len_dist = [0 for i in range(1,100)];
		
		#add root.
		self.num_edges = 0;
		self.num_nodes = 1;
		self.prev_index = -1;

		r = node(root);
		self.node.append(r);
		self.dict[root] = 0;

	def parse_trace(self, trace):
		if re.findall("#",trace):
			return False;

		hops = trace.strip().split('\t');
		
		#record path len to get the dist.
		self.path_len_dist[len(hops)] = self.path_len_dist[len(hops)] + 1;
		
		for i in range(13,len(hops)):
			self.parse_hop(hops[i]);
		return True;

	#see if a node[cind] belongs to node[pind].
	#one pass scan.
	def is_child(self, pind, cind):
		for c in self.node[pind].child:
			if c == cind:
				return True;
	
		return False;

	#each hop contains a tuple of ip,rtt,nTries.
	def parse_hop(self, hop):
		if hop == "q":
			self.prev_index = -1;
			return;

		list = hop.split(';');
		for tuple in list:
			addr = (tuple.split(','))[0];
			rtt = (tuple.split(','))[1];

			#build graph from a trace.
			#self.prev_index represents the index of the predecessor.
			#self.num_nodes-1 is the index of current node being appended.

			#for unseen node: append node, add edge, walk on.
			if not self.dict.has_key(addr):
				self.node.append(node(addr));
				self.dict[addr] = self.num_nodes;
				if self.prev_index != -1:
					self.node[self.prev_index].child.append(self.num_nodes);
					self.node[self.prev_index].child_rtt.append(rtt);
					self.node[self.num_nodes-1].indgree = self.node[self.num_nodes-1].indegree + 1;

					self.num_edges = self.num_edges + 1;

				self.prev_index = self.num_nodes;
				self.num_nodes = self.num_nodes + 1;
			#for existing node: check for different predecessor, the walk on.
			else:
				child_index = self.dict[addr];
				if self.prev_index != -1 and not self.is_child(self.prev_index, child_index):
					self.node[self.prev_index].child.append(child_index);
					self.node[self.prev_index].child_rtt.append(rtt);
					self.node[self.num_nodes-1].indgree = self.node[self.num_nodes-1].indegree + 1;

					self.num_edges = self.num_edges + 1;
				self.prev_index = child_index;
	def build(self, file):
		f = open(file, 'r');
		for line in f.readlines():
			self.prev_index = 0;
			self.parse_trace(line);
			self.num_traces = self.num_traces + 1;
		f.close();
	def disp_stats(self):
		print "total traces processed:",self.num_traces;
		print "total nodes:",len(self.node);
		print "total edges:",self.num_edges;

	
	def draw_topo(self, graph_name):
		graph = nx.Graph();

		for i in range(len(self.node)-1,-1,-1):
			graph.add_node(i);
			for j in range(len(self.node[i].child)):
				graph.add_edge(i,self.node[i].child[j],weight=self.node[i].child_rtt[j]);
						
		#get the largest connected component.
		graph0 = sorted(nx.connected_component_subgraphs(graph), key = len, reverse=True)[0];

		

		
		#get rtt dist.
		#get scalar map for weight.
		rtt_list = [];
		rtt_dist_x = [];
		rtt_dist_y = [];
		

		max_rtt = 0;
		min_rtt = 10000;
		for a,b in graph0.edges():
			rtt = float(graph0[a][b]['weight']);
			rtt_list.append(int(rtt));
			if max_rtt < rtt:
				max_rtt = rtt;
			if min_rtt > rtt:
				min_rtt = rtt;
		
		rtt_list.sort();
		prev_rtt = rtt_list[0];
		rtt_dist_x.append(prev_rtt);
		rtt_dist_y.append(1);
		num_rtt = 0;
		
		for i in range( 1,len(rtt_list) ):
			if rtt_list[i] == prev_rtt:
				rtt_dist_y[num_rtt] = rtt_dist_y[num_rtt] + 1;
			else:
				prev_rtt = rtt_list[i];
				rtt_dist_x.append(rtt_list[i]);
				rtt_dist_y.append(1);
				num_rtt = num_rtt + 1;


		if max_rtt > 100:
			max_rtt = 100;
		rtt_norm = clrs.Normalize(vmin=min_rtt, vmax=max_rtt);
		#use gist_rainbow color map to convert gray scale value to colored rgb.
		scalar_map = cm.ScalarMappable(norm=rtt_norm,cmap=plt.cm.gist_rainbow); 

		#get colors from the scalar map.
		colors = []; 
		for a,b in graph0.edges():
			rgb = scalar_map.to_rgba(graph0[a][b]['weight']);
			colors.append(rgb);

		
		
		#get degree dist.
		#get lablels for high degree nodes.
		labels = {};
		labels[0] = "root:",self.node[0].addr;
		
		degree_list = [];
		deg_dist_x = [];
		deg_dist_y = [];
		
		for n in graph0.nodes():
			degree = self.node[n].indegree+len(self.node[n].child);
			degree_list.append(degree);
			if  degree > 20:
				labels[n] = self.node[n].addr+" ("+str(degree)+")";
		
		degree_list.sort();
		prev_deg = degree_list[0];
		deg_dist_x.append(prev_deg);
		deg_dist_y.append(1);
		num_deg = 0;
		
		for i in range( 1,len(degree_list) ):
			if degree_list[i] == prev_deg:
				deg_dist_y[num_deg] = deg_dist_y[num_deg] + 1;
			else:
				prev_deg = degree_list[i];
				deg_dist_x.append(degree_list[i]);
				deg_dist_y.append(1);
				num_deg = num_deg + 1;
			
		#use graphviz layout to get a hierachical view of the topo.
		plt.figure(figsize=(50,50));
		layout = nx.graphviz_layout(graph0,prog="twopi",root=0);

		#draw topo graph.
		nx.draw(graph0,layout,with_labels=False,alpha=0.5,node_size=15,edge_color=colors);
		nx.draw_networkx_labels(graph0,layout,labels,font_size=10);
		plt.savefig(graph_name+"_topo.png",dpi=300);
		
		#draw deg distribution.
		plt.figure(figsize=(8,8));
		plt.plot(deg_dist_x, deg_dist_y);
		plt.savefig(graph_name+"_deg_dist.png");
		
		#draw deg ccdf.
		plt.figure(figsize=(8,8));
		plt.plot( deg_dist_x, np.cumsum(deg_dist_y) );
		plt.savefig(graph_name+"_deg_ccdf.png");

		#draw deg distribution.
		plt.figure(figsize=(8,8));
		plt.plot(rtt_dist_x, rtt_dist_y);
		plt.savefig(graph_name+"_rtt_dist.png");
		
		#draw deg ccdf.
		plt.figure(figsize=(8,8));
		plt.plot( rtt_dist_x, np.cumsum(rtt_dist_y) );
		plt.savefig(graph_name+"_rtt_ccdf.png");

		#draw path len distribution.
		plt.figure(figsize=(8,8));
		plt.plot([ i for i in range( 1,len(self.path_len_dist)+1 ) ], self.path_len_dist);
		plt.savefig(graph_name+"_path_len_dist.png");
		
		#draw path len ccdf.
		plt.figure(figsize=(8,8));
		plt.plot([ i for i in range( 1,len(self.path_len_dist)+1 ) ], np.cumsum(self.path_len_dist));
		plt.savefig(graph_name+"_path_len_ccdf.png");



		
def get_src(file_name):
	f = open(file_name,'r');
	for line in f.readlines():
		if re.findall("#",line):
			continue;
		list = line.strip().split('\t');
		src = list[1];
		f.close();
		return src;

def main(argv):
	if len(argv) != 3:
		print "usage:python merge.py <dump_file_name> <output_prefix>";
		return;

	topo = dag(get_src(argv[1]));
	topo.build(argv[1]);
	topo.disp_stats();
	topo.draw_topo(argv[2]);

if __name__ == "__main__":
	main(sys.argv);

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
		
		#rtt.
		self.max_rtt = 0;
		self.min_rtt = 10000;
		self.rtt_list = [];
		self.rtt_dist_x = [];
		self.rtt_dist_y = [];


		#deg.
		self.degree_list = [];
		self.deg_dist_x = [];
		self.deg_dist_y = [];

		#networkx topo graph.
		self.graph = nx.Graph();
		#largest connected component.
		self.graph0 = nx.Graph();

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

		for i in range(len(self.node)-1,-1,-1):
			self.graph.add_node(i);
			for j in range(len(self.node[i].child)):
				self.graph.add_edge(i,self.node[i].child[j],weight=self.node[i].child_rtt[j]);
						
		#get the largest connected component.
		self.graph0 = sorted(nx.connected_component_subgraphs(self.graph), key = len, reverse=True)[0];

	def disp_stats(self):
		print "total traces processed:",self.num_traces;
		print "total nodes:",len(self.node);
		print "total edges:",self.num_edges;

	def draw_rtt(self, graph_name):
		#get rtt dist.
		self.max_rtt = 0;
		self.min_rtt = 10000;
		for a,b in self.graph0.edges():
			rtt = float(self.graph0[a][b]['weight']);
			self.rtt_list.append(int(rtt));
			if self.max_rtt < rtt:
				self.max_rtt = rtt;
			if self.min_rtt > rtt:
				self.min_rtt = rtt;
		
		self.rtt_list.sort();
		prev_rtt = self.rtt_list[0];
		self.rtt_dist_x.append(prev_rtt);
		self.rtt_dist_y.append(1);
		num_rtt = 0;
		
		for i in range( 1,len(self.rtt_list) ):
			if self.rtt_list[i] == prev_rtt:
				self.rtt_dist_y[num_rtt] = self.rtt_dist_y[num_rtt] + 1;
			else:
				prev_rtt = self.rtt_list[i];
				self.rtt_dist_x.append(self.rtt_list[i]);
				self.rtt_dist_y.append(1);
				num_rtt = num_rtt + 1;
		
		#draw rtt distribution.
		plt.figure(figsize=(8,8));
		plt.yscale('log');
		plt.xscale('log');

		plt.plot(self.rtt_dist_x, self.rtt_dist_y);
		plt.savefig(graph_name+"_rtt_dist.png");
		
		#draw rtt ccdf.
		plt.figure(figsize=(8,8));
		plt.yscale('log');
		plt.xscale('log');

		plt.plot( self.rtt_dist_x, np.cumsum(self.rtt_dist_y) );
		plt.savefig(graph_name+"_rtt_ccdf.png");

	def draw_deg(self, graph_name):
		#get degree dist.
		for n in self.graph0.nodes():
			degree = self.node[n].indegree+len(self.node[n].child);
			self.degree_list.append(degree);
		
		temp_list = sorted(self.degree_list);
		prev_deg = temp_list[0];
		self.deg_dist_x.append(prev_deg);
		self.deg_dist_y.append(1);
		num_deg = 0;
		
		for i in range( 1,len(temp_list) ):
			if temp_list[i] == prev_deg:
				self.deg_dist_y[num_deg] = self.deg_dist_y[num_deg] + 1;
			else:
				prev_deg = temp_list[i];
				self.deg_dist_x.append(temp_list[i]);
				self.deg_dist_y.append(1);
				num_deg = num_deg + 1;

		
		#draw deg distribution.
		plt.figure(figsize=(8,8));
		plt.yscale('log');
		plt.xscale('log');

		plt.plot(self.deg_dist_x, self.deg_dist_y);
		plt.savefig(graph_name+"_deg_dist.png");
		
	def draw_path(self,graph_name):
		#draw path len distribution.
		plt.figure(figsize=(8,8));

		plt.plot([ i for i in range( 1,len(self.path_len_dist)+1 ) ], self.path_len_dist);
		plt.savefig(graph_name+"_path_len_dist.png");
		
		#draw path len ccdf.
		plt.figure(figsize=(8,8));

		plt.plot([ i for i in range( 1,len(self.path_len_dist)+1 ) ], np.cumsum(self.path_len_dist));
		plt.savefig(graph_name+"_path_len_ccdf.png");


	def draw_topo(self, graph_name):
		#get scalar map for weight.
		max_rtt = self.max_rtt;
		min_rtt = self.min_rtt;
		if self.max_rtt > 100:
			max_rtt = 100;
		rtt_norm = clrs.Normalize(vmin=min_rtt, vmax=max_rtt);
		#use gist_rainbow color map to convert gray scale value to colored rgb.
		scalar_map = cm.ScalarMappable(norm=rtt_norm,cmap=plt.cm.gist_rainbow); 

		#get colors from the scalar map.
		colors = []; 
		for a,b in self.graph0.edges():
			rgb = scalar_map.to_rgba(self.graph0[a][b]['weight']);
			colors.append(rgb);
		

		#get lablels for high degree nodes.
		labels = {};
		labels[0] = "root:",self.node[0].addr;

		for i in range( len(self.degree_list) ):
			degree = self.degree_list[i];
			if  degree > 20:
				labels[i] = self.node[i].addr+" ("+str(degree)+")";
		
		#use graphviz layout to get a hierachical view of the topo.
		plt.figure(figsize=(50,50));
		layout = nx.graphviz_layout(self.graph0,prog="twopi",root=0);

		#draw topo graph.
		nx.draw(self.graph0,layout,with_labels=False,alpha=0.5,node_size=15,edge_color=colors);
		nx.draw_networkx_labels(self.graph0,layout,labels,font_size=10);
		plt.savefig(graph_name+"_topo.png",dpi=300);
		
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

	topo.draw_path(argv[2]);
	topo.draw_rtt(argv[2]);
	topo.draw_deg(argv[2]);

	topo.draw_topo(argv[2]);

if __name__ == "__main__":
	main(sys.argv);

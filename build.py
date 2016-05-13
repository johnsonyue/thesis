import sys
reload(sys);
sys.setdefaultencoding('utf-8');
import re
import time

import matplotlib
matplotlib.use("Agg");
import matplotlib.pyplot as plt
import matplotlib.colors as clrs
import matplotlib.cm as cm

import numpy as np

import networkx as nx
from networkx import graphviz_layout

import geoip2.database

from mpl_toolkits.basemap import Basemap

#class node represents a node in topo graph.
class node:
	def __init__(self,ip):
		self.addr = ip;
		self.country_code = "";
		self.is_border = False;
		self.loc_desc = "";
		self.lon = 0;
		self.lat = 0;

		self.child = [];
		self.child_rtt = [];
		
		self.indegree = 0;

#topo graph is a directed graph.
class topo_graph:
	def __init__(self, root):
		#nodes.
		self.node = [];
		#dict for quick node lookup.
		self.dict = {};
		
		#stats for traces.
		self.num_traces = 0;
		self.path_len_dist = [0 for i in range(1,100)];
		
		#add root.
		self.num_edges = 0;
		self.num_nodes = 1;
		self.num_border = 0;
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
		
		self.visited = [];
	
	def clear_visited(self):
		for i in range(self.num_nodes):
			self.visited[i] = False;
		
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
		
		#query country.
		reader = geoip2.database.Reader('GeoLite2-City.mmdb');
		for i in range( len(self.node) ):
			is_found = True;
			iso_code = "";
			loc_desc_list = ["*","*","*"];

			lon = 0;
			lat = 0;
			try:
				response = reader.city(self.node[i].addr);
			except geoip2.errors.AddressNotFoundError:
				is_found = False;
			finally:
				if not is_found:
					iso_code = "*";
					loc_desc = "*";
				else:
					lon = response.location.longitude;
					lat = response.location.latitude;
					
					iso_code = response.country.iso_code;
					city_name = response.city.name;
					subdiv_name = response.subdivisions.most_specific.name;
					loc_desc_list = ["*","*","*"];
					if city_name != None:
						loc_desc_list[0] = city_name;
					if subdiv_name != None:
						loc_desc_list[1] = subdiv_name;
					if iso_code != None:
						loc_desc_list[2] = iso_code;

			self.node[i].country_code = iso_code;
			self.node[i].loc_desc = loc_desc_list[0]+","+loc_desc_list[1]+","+loc_desc_list[2];
			self.node[i].lon = lon;
			self.node[i].lat = lat;

		reader.close();

		for i in range(len(self.node)-1,-1,-1):
			self.graph.add_node(i);
			for j in range(len(self.node[i].child)):
				self.graph.add_edge(i,self.node[i].child[j],weight=self.node[i].child_rtt[j]);
						
		#get the largest connected component.
		self.graph0 = sorted(nx.connected_component_subgraphs(self.graph), key = len, reverse=True)[0];
		
		for i in range(self.num_nodes):
			self.visited.append(False);
		
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


	def draw_topo_graphviz(self, graph_name):
		print "\tsetting colors for edges... ",;
		#get scalar map for weight.
		max_rtt = self.max_rtt;
		min_rtt = self.min_rtt;
		if self.max_rtt > 100:
			max_rtt = 100;
		rtt_norm = clrs.Normalize(vmin=min_rtt, vmax=max_rtt);
		#use gist_rainbow color map to convert gray scale value to colored rgb.
		scalar_map = cm.ScalarMappable(norm=rtt_norm,cmap=plt.cm.gist_rainbow); 

		#get edge colors from the scalar map.
		edge_colors = []; 
		for a,b in self.graph0.edges():
			rgb = scalar_map.to_rgba(self.graph0[a][b]['weight']);
			edge_colors.append(rgb);
		print "done";
		
		
		print "\tsetting colors for nodes... ",;
		node_colors = [];
		for n in self.graph0.nodes():
			color = 'r'
			if self.node[n].is_border:
				color = 'b';
			node_colors.append(color);
		print "done";
		

		print "\tsetting labels for nodes... ",;
		#get lablels for high degree nodes.
		labels = {};
		labels[0] = "root:",self.node[0].addr;

		for n in self.graph0.nodes():
			degree = self.node[n].indegree+len(self.node[n].child);
			if degree > 20:
				labels[n] = self.node[n].addr+" ("+str(degree)+")";

		print "done";
		
		print "\texecuting graphviz... ",;
		#use graphviz layout to get a hierachical view of the topo.
		plt.figure(figsize=(50,50));
		layout = nx.graphviz_layout(self.graph0,prog="twopi",root=0);
		print "done";

		print "\tsaving pic.. ",;
		#draw topo graph.
		nx.draw(self.graph0,layout,with_labels=False,alpha=0.5,node_size=15,edge_color=edge_colors,node_color=node_colors);
		nx.draw_networkx_labels(self.graph0,layout,labels,font_size=10);
		plt.savefig(graph_name+"_topo.png",dpi=300);
		print "done";
	
	def recursive_mark(self, parent_code, root):
		self.visited[root] = True;
		root_code = self.node[root].country_code;
		if root_code == None or root_code == "*":
			root_code = parent_code;
		if root_code != parent_code:
			self.node[root].is_border = True;
		
		for c in self.node[root].child:
			child_code = self.node[c].country_code;
			if child_code != None and child_code != "*" and root_code != child_code:
				self.node[root].is_border = True;

			if not self.visited[c]:
				self.recursive_mark(root_code, c);

		if self.node[root].is_border:
			self.num_border = self.num_border + 1;

	#sample 20 dots on line segment between start and end.
	def get_dots(self, start ,end):
		x = [];
		y = [];
		delta_x = (end[0] - start[0]);
		delta_y = (end[1] - start[1]);
		if start[0] != end[0]:
			for i in range(21):
				x.append(start[0] + delta_x/20.0*i);
				y.append(start[1] + delta_y/delta_x*(x[i]-start[0]));
		else:
			for i in range(21):
				x.append(start[0]);
				y.append(start[1] + delta_y/20.0*i);
		return x, y;
	
	#added path to avoid looping.
	def recursive_draw_map(self, basemap, parent_lonlat, root):
		self.visited[root] = True;
		
		child_lonlat = parent_lonlat;
		if len( self.node[root].child ) != 0:
			c0 = self.node[root].child[0];
			child_lonlat = (self.node[c0].lon, self.node[c0].lat);
			if (child_lonlat[0] == None or child_lonlat[1] == None):
				child_lonlat = (0, 0);


		root_lonlat = (self.node[root].lon, self.node[root].lat);
		if (root_lonlat[0] == None or root_lonlat[1] == None):
			root_lonlat = (0, 0);
		if root_lonlat == (0, 0):
			lon = (parent_lonlat[0]+child_lonlat[0])/2.0;
			lat = (parent_lonlat[1]+child_lonlat[1])/2.0;
			root_lonlat = (lon, lat);
		basemap.plot(root_lonlat[0], root_lonlat[1], latlon=True, marker = 'o', markerfacecolor='red', markersize=1.5);
		x,y = self.get_dots(parent_lonlat, root_lonlat);
		basemap.plot(x, y, latlon=True, linewidth=0.3, color='r');

		for c in self.node[root].child:
			if not self.visited[c]:
				self.recursive_draw_map(basemap, root_lonlat, c);

	
	def draw_map(self, graph_name):
		plt.figure(figsize=(50,50));

		#draw background.
		m = Basemap( projection = 'mill',\
		             resolution = 'i',\
		             llcrnrlon = -180.,\
		             llcrnrlat = -90.,\
		             urcrnrlon = 180.,\
		             urcrnrlat = 90.);

		m.drawmapboundary(fill_color='aqua');
		m.fillcontinents(color = 'coral', lake_color= 'aqua');
		m.drawcountries();
		m.drawparallels(np.arange(-90,90,30), labels=[1,1,0,0], linewidth=0.8, color='g');
		m.drawmeridians(np.arange(-180,180,30), labels=[0,0,1,1], linewidth=0.8, color='g');

		self.clear_visited();
		#draw nodes and paths.
		self.recursive_draw_map(m, (self.node[0].lon, self.node[0].lat), 0);

		plt.savefig(graph_name+"_map.png",dpi=300);
	
	def export(self, graph_name):
		f_topo = open(graph_name+"_topo", 'w');
		f_node = open(graph_name+"_node", 'w');
		
		for i in range(len(self.node)):
			f_topo.write(str(i));
			node = self.node[i];
			for c in node.child:
				f_topo.write(","+str(c));
			f_topo.write('\n');
			
			lon = node.lon;
			lat = node.lat;
			if(lon == None or lat == None):
				lon = 0;
				lat = 0;

			f_node.write("%d,%s,%d,%s,%.2f,%.2f\n"%(i,node.addr,node.is_border,node.country_code,lon,lat));

		f_topo.close();
		f_node.close();
			
				
		
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

	topo = topo_graph(get_src(argv[1]));
	
	print "building..., ",;
	start_time = time.time();
	topo.build(argv[1]);
	end_time = time.time();
	print (end_time - start_time)*1000,"ms";
	topo.disp_stats();
	
	print "drawing path..., ",;
	start_time = time.time();
	topo.draw_path(argv[2]);
	end_time = time.time();
	print (end_time - start_time)*1000,"ms";

	#call draw_rtt to get max_rtt & min_rtt & dist_rtt.
	print "drawing rtt..., ",;
	start_time = time.time();
	topo.draw_rtt(argv[2]);
	end_time = time.time();
	print (end_time - start_time)*1000,"ms";

	#call draw_deg to get dist deg.
	print "drawing deg..., ",;
	start_time = time.time();
	topo.draw_deg(argv[2]);
	end_time = time.time();
	print (end_time - start_time)*1000,"ms";

	#mark border.
	print "marking border..., ";
	start_time = time.time();
	topo.clear_visited();
	topo.recursive_mark(topo.node[0].country_code, 0);
	end_time = time.time();
	print "\tborder ip num:", topo.num_border;
	print "\t",(end_time - start_time)*1000,"ms";

	print "drawing topo..., ";
	start_time = time.time();
	topo.draw_topo_graphviz(argv[2]);
	end_time = time.time();
	print "\t",(end_time - start_time)*1000,"ms";
	
	print "drawing map..., ";
	start_time = time.time();
	#topo.draw_map(argv[2]);
	end_time = time.time();
	print "\t",(end_time - start_time)*1000,"ms";
	
	print "exporting...";
	start_time = time.time();
	topo.export(argv[2]);
	end_time = time.time();
	print "\t",(end_time - start_time)*1000,"ms";
	
	
if __name__ == "__main__":
	main(sys.argv);

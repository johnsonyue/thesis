import sys
import os
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
from networkx.drawing.nx_agraph import graphviz_layout

import geoip2.database
import lookup

from mpl_toolkits.basemap import Basemap

import json

import qqwry

#class node represents a node in topo graph.
class node:
	def __init__(self,ip):
		self.addr = ip;
		self.country_code = "";
		self.asn = "";
		self.asn_cc = "";
		self.czdb_country = "";
		self.czdb_area = "";
		self.is_border = False;
		self.is_ascc_border = False;
		self.lon = 0;
		self.lat = 0;

		self.child = [];
		self.child_rtt = [];
		self.parent = [];
		
		self.indegree = 0;

#topo graph is a directed graph.
class topo_graph:
	def __init__(self, root, is_lookup=True):
		#nodes.
		self.node = [];
		#dict for quick node lookup.
		self.dict = {};
		
		#stats for traces.
		self.num_traces = 0;
		self.path_len_dist = [0 for i in range(1,100)];
		#path tree.
		self.ptr=[];
		self.path_tree = [];

		if (is_lookup):
			#ip lookup.
			self.lkp = lookup.lookup();
		else:
			self.lkp = None;
			
		#czdb.
		self.czdb_path = "qqwry.dat";
    		if not os.path.exists(self.czdb_path):
        		qqwry.update_db(self.czdb_path);
    		self.qqwry = qqwry.QQWry(self.czdb_path);
		
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
		
		self.bet = {};
		self.bet_dist = [0 for i in range(100)];

		self.map_nodes = [];
		self.map_nodes_dict = {};
		self.map_paths = [];
		self.map_paths_dict = {};
		
		#data structure for simplified topo.
		self.data = {"nodes":{}, "edges":[]};
		
		self.visited = [];
		
		#knn.
		self.knn = {};
	
	def clear_visited(self):
		for i in range(self.num_nodes):
			self.visited[i] = False;
		
	def parse_trace(self, trace):
		if re.findall("#",trace):
			return False;

		hops = trace.strip().split('\t');
		
		#record path len to get the dist.
		self.path_len_dist[len(hops)] = self.path_len_dist[len(hops)] + 1;
		
		self.ptr = self.path_tree;
		for i in range(13,len(hops)):
			hop = hops[i].split(';')[0];
			hop_list = [];
			if hop != "q":
				addr = hop.split(',')[0];
				rtt = hop.split(',')[1];
				hop_list = [addr, rtt];
			self.parse_hop(hop_list);
		return True;
	
	def parse_trace_iplane(self, trace_list):
		#record path len to get the dist.
		self.path_len_dist[len(trace_list)] = self.path_len_dist[len(trace_list)] + 1;

		self.ptr = self.path_tree;
		for i in range(len(trace_list)):
			hop = trace_list[i];
			hop_list = [];
			addr = hop.split(' ')[1];
			rtt = hop.split(' ')[2];
			
			if (addr != "0.0.0.0"):
				hop_list = [addr, rtt];
			self.parse_hop(hop_list);

		return True;

	#see if a node[cind] belongs to node[pind].
	#one pass scan.
	def is_child(self, pind, cind):
		for c in self.node[pind].child:
			if c == cind:
				return True;
	
		return False;
	
	def add_parent(self, cind, pind):
		is_included = False;
		for p in self.node[cind].parent:
			if p == pind:
				is_included = True;
				break;
		
		if (is_included):
			self.node[cind].parent.append(pind);

	#each hop contains a tuple of ip,rtt,nTries.
	def parse_hop(self, hop):
		if hop == []:
			self.prev_index = -1;
			return;

		addr = hop[0];
		rtt = hop[1];
		
		cnt = -1;
		#asn.
		if (self.lkp):
			asn = self.lkp.get_asn_from_pfx(addr);
		else:
			asn = None;
		if (asn == None):
			asn = "*";
			asn_cc = "*";
		if (asn != "*"):
			asn_cc = self.lkp.get_cc_from_asn(asn);
		
		is_included = False;
		for i in range(len(self.ptr)):
			if self.ptr[i]["name"] == asn:
				is_included = True;
				cnt = i;
				break;
			cnt = i;
		
		if(not is_included):
			root = {"name":asn, "asn_cc":asn_cc, "num":1, "children":[]};
			self.ptr.append(root);
		else:
			self.ptr[cnt]["num"] = self.ptr[cnt]["num"] + 1;
		
		self.ptr = self.ptr[cnt]["children"];
				
		#build graph from a trace.
		#self.prev_index represents the index of the predecessor.
		#self.num_nodes-1 is the index of current node being appended.

		#for unseen node: append node, add edge, walk on.
		if not self.dict.has_key(addr):
			self.node.append(node(addr));
			if(self.prev_index != -1):
				self.add_parent(self.num_nodes, self.prev_index);
			self.dict[addr] = self.num_nodes;
			self.node[self.num_nodes].asn = asn;
			self.node[self.num_nodes].asn_cc = asn_cc;
			if self.prev_index != -1:
				self.node[self.prev_index].child.append(self.num_nodes);
				self.node[self.prev_index].child_rtt.append( (0, self.prev_index, rtt) );
				self.node[self.num_nodes-1].indgree = self.node[self.num_nodes-1].indegree + 1;

				self.num_edges = self.num_edges + 1;

			self.prev_index = self.num_nodes;
			self.num_nodes = self.num_nodes + 1;
		#for existing node: check for different predecessor, the walk on.
		else:
			child_index = self.dict[addr];
			if(self.prev_index != -1):
				self.add_parent(child_index, self.prev_index);

			if self.prev_index != -1 and not self.is_child(self.prev_index, child_index):
				self.node[self.prev_index].child.append(child_index);
				self.node[self.prev_index].child_rtt.append( (0, self.prev_index, rtt) );
				self.node[self.num_nodes-1].indgree = self.node[self.num_nodes-1].indegree + 1;

				self.num_edges = self.num_edges + 1;

			self.prev_index = child_index;
	
	def query_cc(self):
		#query asn_cc for root.
		if (self.lkp):
			asn = self.lkp.get_asn_from_pfx(self.node[0].addr);
		else:
			asn = None;
		if (asn == None):
			asn = "*";
			asn_cc = "*";
		if (asn != "*"):
			asn_cc = self.lkp.get_cc_from_asn(asn);
		
		self.node[0].asn = asn;
		self.node[0].asn_cc = asn_cc;

		print "querying cc...";
		#query country.
		reader = geoip2.database.Reader('GeoLite2-City.mmdb');

		for i in range( len(self.node) ):
			#maxmind.
			is_found = True;
			iso_code = "";

			lon = 0;
			lat = 0;
			try:
				response = reader.city(self.node[i].addr);
			except geoip2.errors.AddressNotFoundError:
				is_found = False;
			finally:
				if not is_found:
					iso_code = "*";
				else:
					lon = response.location.longitude;
					lat = response.location.latitude;
					
					iso_code = response.country.iso_code;

			self.node[i].country_code = iso_code;
			self.node[i].lon = lon;
			self.node[i].lat = lat;

			#czdb.
			self.node[i].czdb_country, self.node[i].czdb_area = self.qqwry.query(self.node[i].addr);
		
		reader.close();


	def build(self, file, source, is_query_cc=True, is_mark_border=True):
		print "parsing traces...";
		if(source == "caida"):
			f = open(file, 'r');
			for line in f.readlines():
				self.prev_index = 0;
				self.parse_trace(line);
				self.num_traces = self.num_traces + 1;
			f.close();
		elif(source == "iplane"):
			f = open(file, 'r');
			trace_list = [];
			lines = f.readlines();
			i = 0;
			for line in lines:
				is_delimiter = False;
				if re.findall("read",line) or re.findall("dest",line):
					is_delimiter = True;
				else:
					trace_list.append(line.strip('\n'));
				
				if i >= len(lines)-1 or (is_delimiter == True and len(trace_list) != 0):
					self.num_traces = self.num_traces + 1;
					self.prev_index = 0;
					self.parse_trace_iplane(trace_list);
					trace_list = [];
				
				i = i+1;

			f.close();
		
		if (is_query_cc):
			self.query_cc();

		print "building networkx object...";
		for i in range(len(self.node)-1,-1,-1):
			self.graph.add_node(i);
			for j in range(len(self.node[i].child)):
				self.graph.add_edge(i,self.node[i].child[j],weight=self.node[i].child_rtt[j][2]);
						
		print "getting the largest connected component...";
		#get the largest connected component.
		#self.graph0 = sorted(nx.connected_component_subgraphs(self.graph), key = len, reverse=True)[0];
		self.graph0 = max(nx.connected_component_subgraphs(self.graph), key = len);
		
		for i in range(self.num_nodes):
			self.visited.append(False);
		
		if(is_mark_border):
			#mark borders.
			print "marking borders...";
			self.clear_visited();
			self.mark_borders();
			print "borders marked";
		
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
	
	#if node doesn't have the cc, assume it to be within the same cc of it's parent.
	def recursive_mark(self, parent_code, parent_ascc, root):
		self.visited[root] = True;

		root_code = self.node[root].country_code;
		root_ascc = self.node[root].asn_cc;
		if root_code == None or root_code == "*":
			root_code = parent_code;
		if root_ascc == "*":
			root_ascc = parent_ascc;

		if root_code != parent_code:
			self.node[root].is_border = True;
		if root_ascc != parent_ascc:
			self.node[root].is_ascc_border = True;
		
		for c in self.node[root].child:
			child_code = self.node[c].country_code;
			child_ascc = self.node[c].asn_cc;
			if child_code != None and child_code != "*" and root_code != child_code:
				self.node[root].is_border = True;
			if child_ascc != "*" and root_ascc != child_ascc:
				self.node[root].is_ascc_border = True;
			
			if not self.visited[c]:
				self.recursive_mark(root_code, root_ascc, c);

		if self.node[root].is_border:
			self.num_border = self.num_border + 1;
	
	def mark_borders(self):
		self.recursive_mark(self.node[0].country_code, self.node[0].asn_cc, 0);

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
	def recursive_generate_map(self, parent_lonlat, root):
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
		
		if (not self.map_nodes_dict.has_key(str(root_lonlat))):
			self.map_nodes_dict[str(root_lonlat)] = len(self.map_nodes);
			self.map_nodes.append( { "lon":root_lonlat[0], "lat":root_lonlat[1] } );

		is_redundant = False;
		if (self.map_paths_dict.has_key(str(parent_lonlat))):
			if (self.map_paths_dict[str(parent_lonlat)].has_key(str(root_lonlat))):
				is_redundant = True;
			else:
				self.map_paths_dict[str(parent_lonlat)][str(root_lonlat)] = 1;
		else:
			self.map_paths_dict[str(parent_lonlat)] = { str(root_lonlat):1 };
		
		if (not is_redundant):
			parent_index = self.map_nodes_dict[str(parent_lonlat)];
			root_index = self.map_nodes_dict[str(root_lonlat)];
			if parent_index != root_index:
				path = { "source":parent_index, "target":root_index };
				self.map_paths.append( path );
		
		for c in self.node[root].child:
			if not self.visited[c]:
				self.recursive_generate_map(root_lonlat, c);

	
		
	def generate_map(self):
		self.clear_visited();
		#draw nodes and paths.
		self.recursive_generate_map((self.node[0].lon, self.node[0].lat), 0);
		
		
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
		
		for i in range(len(self.map_paths)):
			src = self.map_paths[i]["source"];
			tgt = self.map_paths[i]["target"];
			parent_lonlat = (self.map_nodes[src]["lon"], self.map_nodes[src]["lat"]);
			root_lonlat = (self.map_nodes[tgt]["lon"], self.map_nodes[tgt]["lat"]);
			
			x,y = self.get_dots(parent_lonlat, root_lonlat);
			m.plot(x, y, latlon=True, linewidth=0.3, color='r');

		for i in range(len(self.map_nodes)):
			m.plot(self.map_nodes[i]["lon"], self.map_nodes[i]["lat"], latlon=True, marker = 'o', markerfacecolor='red', markersize=1.5);
		
		plt.savefig(graph_name+"_map.png",dpi=300);

	def calc_knn(self):
		deg_num = {};
		n_deg = {};
		for i in range( 1,len(self.node) ):
			degree = self.node[i].indegree+len(self.node[i].child);
			if (deg_num.has_key(degree)):
				deg_num[degree] = deg_num[degree] + 1;
			else:
				deg_num[degree] = 1;
			
			if ( not n_deg.has_key(degree) ):
				n_deg[degree] = {};
			for c in self.node[i].child:
				cdegree = self.node[c].indegree+len(self.node[c].child);
				if (n_deg[degree].has_key(cdegree)):
					n_deg[degree][cdegree] = n_deg[degree][cdegree] + 1;
				else:
					n_deg[degree][cdegree] = 1;
			for p in self.node[i].parent:
				pdegree = self.node[p].indegree+len(self.node[p].child);
				if (n_deg[degree].has_key(pdegree)):
					n_deg[degree][pdegree] = n_deg[degree][pdegree] + 1;
				else:
					n_deg[degree][pdegree] = 1;
		
		#calc_knn.
		for d in deg_num.keys():
			exp=0;
			for k in n_deg[d].keys():
				exp = exp + (float)(k*n_deg[d][k])/deg_num[d];
			
			self.knn[d] = exp;
				
	
	def export_topo(self, graph_name):
		f_topo = open(graph_name+"_topo", 'w');
		f_node = open(graph_name+"_topo_node", 'w');
		
		for i in self.graph0.nodes():
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
	
	def export_topo_simplified(self, graph_name):
		f_data = open(graph_name+"_topo_simple", 'w');
		
		self.clear_visited();
		
		self.export_subtopo(0, 0);
		result = {"nodes":[], "edges":[]};
		map = {};
		
		i = 0;
		nodes = self.data["nodes"];
		for k in nodes:
			map[k] = i;
			i = i+1;
		
		for k in nodes:
			result["nodes"].append(nodes[k]);
		
		edges = self.data["edges"];
		for e in edges:
			t = {"source" : map[e["source"]], "target" : map[e["target"]]};
			result["edges"].append(t); 
		
		f_data.write(json.dumps(result));
		f_data.close();
	
	def export_subtopo(self, ind, hop):
		node = self.node[ind];

		n = {"addr":node.addr, "is_border":node.is_border, "country":node.country_code, "lon":node.lon, "lat":node.lat};
		self.data["nodes"][ind] = n;
		
		self.visited[ind] = True;
		
		if hop <= 4:
			for c in node.child:
				if not self.visited[c]:
					link = {"source":ind, "target":c};
					self.data["edges"].append(link);
					self.export_subtopo(c, hop+1);
		
		
	def export_map(self, graph_name):
		f_map = open(graph_name+".map", 'w');
		f_node = open(graph_name+"_map_node.json", 'w');
		f_data = open(graph_name+"_map_data.json", 'w');
				
		f_map.write(json.dumps(self.map_paths));
		f_node.write(json.dumps(self.map_nodes));
		data = {};
		data["nodes"] = self.map_nodes;
		data["edges"] = self.map_paths;
		f_data.write(json.dumps(data));
		
		f_map.close();
		f_node.close();
	
	def export_graphviz(self, graph_name):
		pos = nx.graphviz_layout(self.graph0,prog="twopi",root=0);
		map = {};
		result = {"nodes":[], "edges":[]};

		i = 0;
		for n in self.graph0.nodes():
			node = self.node[n];
			p = pos[n];
			t = {"addr":node.addr, "is_border":node.is_border, "country":node.country_code, "lon":node.lon, "lat":node.lat, "pos":p};
			result["nodes"].append(t);

			map[n] = i;
			i = i+1;
		
		for a,b in self.graph0.edges():
			e = {"source": map[a], "target": map[b]};
			result["edges"].append(e);

		f_viz = open(graph_name+".graphviz", 'w');
		f_viz.write(json.dumps(result));
		f_viz.close();
	
	def export_degree(self, graph_name):
		result = {"nodes":[]};

		for n in self.graph0.nodes():
			node = self.node[n];
			degree = node.indegree+len(node.child);

			t = {"addr":node.addr, "is_border":node.is_border, "country":node.country_code, "lon":node.lon, "lat":node.lat, "degree":degree};
			result["nodes"].append(t);

		f_deg = open(graph_name+".degree", 'w');
		f_deg.write(json.dumps(result));
		f_deg.close();
	
	def export_path_tree(self, graph_name):
		asn = self.lkp.get_asn_from_pfx(self.node[0].addr);
		ascc = self.lkp.get_cc_from_asn(asn);
		result = {"name":asn, "as_cc":ascc, "num":self.num_traces, "children":self.path_tree};

		f_pt = open(graph_name+".pt", 'w');
		f_pt.write(json.dumps(result));
		f_pt.close();
	
	def export_border_ip(self, graph_name):
		result = {"nodes":[]};

		for n in self.graph0.nodes():
			node = self.node[n];
			t = {"addr":node.addr, "country":node.country_code, "asn":node.asn, "asn_cc":node.asn_cc, "czdb_country":node.czdb_country, "czdb_area":node.czdb_area};
			result["nodes"].append(t);

		fb = open(graph_name+".border", 'w');
		fb.write(json.dumps(result));
		fb.close();
		
	def merge(self, topo):
		list = topo.node;
		graph = topo.graph0.nodes();
		topo.clear_visited();
		for i in graph:
			if not topo.visited[i]:
				self.add_node(topo, i, topo.node[i]);
	
	def add_node(self, topo, ind, n):
		index = -1;
		list = topo.node;
		
		topo.visited[ind] = True;
		
		#recursively get child.
		child = [];
		for c in n.child:
			if not topo.visited[c]:
				ret = self.add_node(topo, c, list[c]);
				child.append(ret);

		#set index to return.
		#append or update node.
		if not self.dict.has_key(n.addr):
			self.node.append(n);
			index = len(self.node);
			n.child = child;
		else:
			index = self.dict[n.addr];
			for c in child:
				is_included = False;
				for ch in self.node[index].child:
					if c == ch:
						is_included = True;
						break;
				if not is_included:
					self.node[index].child.append(c);
	
		return index;
		
def get_src(file_name):
	f = open(file_name,'r');
	for line in f.readlines():
		if re.findall("#",line):
			continue;
		list = line.strip().split('\t');
		src = list[1];
		f.close();
		return src;

def get_src_iplane(file_name):
	f = open(file_name,'r');
	for line in f.readlines():
		if re.findall("read",line) or re.findall("dest",line):
			continue;
		addr = line.split(' ')[1];
		if (addr != "0.0.0.0"):
			f.close();
			return addr;

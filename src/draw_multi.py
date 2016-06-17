import ip_topo
import caida
import numpy as np
import matplotlib
matplotlib.use("Agg");
import matplotlib.pyplot as plt

file_08 = [];
#file_12 = [];
file_16 = [];


print("building topo_08");
url_list = caida.get_time_list("caida","20080617");
dir = "data/caida/ip/20080617/all/";
for u in url_list:
	time = u.split('/')[9].split('.')[4];
	node = u.split('/')[9].split('.')[5];
	if(time=="20080617"):
		raw_file = "caida.ip."+time+"."+node;
		file_08.append(raw_file);

topo_08 = ip_topo.topo_graph(ip_topo.get_src(dir+file_08[0]),False);
topo_08.build(dir+file_08[0],"caida",False,False);
for i in range(1, len(file_08)):
	topo = ip_topo.topo_graph(ip_topo.get_src(dir+file_08[i]),False);
	topo.build(dir+file_08[i],"caida",False,False);
	topo_08.merge(topo);
	print str(i+1)+" of "+str(len(file_08))+" done.";

'''
print("building topo_12");
url_list = caida.get_time_list("caida","20120617");
dir = "data/caida/ip/20120617/all/";
for u in url_list:
	time = u.split('/')[9].split('.')[4];
	node = u.split('/')[9].split('.')[5];
	if(time=="20120617"):
		raw_file = "caida.ip."+time+"."+node;
		file_12.append(raw_file);

topo_12 = ip_topo.topo_graph(ip_topo.get_src(dir+file_12[0]),False);
topo_12.build(dir+file_12[0],"caida",False,False);
for i in range(1, len(file_12)):
	topo = ip_topo.topo_graph(ip_topo.get_src(dir+file_12[i]),False);
	topo.build(dir+file_12[i],"caida",False,False);
	topo_12.merge(topo);
	print str(i+1)+" of "+str(len(file_12))+" done.";
'''

print("building topo_16");
url_list = caida.get_time_list("caida","20160528");
dir = "data/caida/ip/20160528/all/";
for u in url_list:
	time = u.split('/')[9].split('.')[4];
	node = u.split('/')[9].split('.')[5];
	if(time=="20160528"):
		raw_file = "caida.ip."+time+"."+node;
		file_16.append(raw_file);

topo_16 = ip_topo.topo_graph(ip_topo.get_src(dir+file_16[0]),False);
topo_16.build(dir+file_16[0],"caida",False,False);
for i in range(1, len(file_16)):
	topo = ip_topo.topo_graph(ip_topo.get_src(dir+file_16[i]),False);
	topo.build(dir+file_16[i],"caida",False,False);
	topo_08.merge(topo);
	print str(i+1)+" of "+str(len(file_16))+" done.";


degree_list_08 = [];
#degree_list_12 = [];
degree_list_16 = [];

def get_temp_list(degree_list):
	temp_list = sorted(degree_list);
	prev_deg = temp_list[0];
	deg_dist_x = [prev_deg];
	deg_dist_y = [1];
	num_deg = 0;

	for i in range( 1,len(temp_list) ):
		if temp_list[i] == prev_deg:
			deg_dist_y[num_deg] = deg_dist_y[num_deg] + 1;
		else:
			prev_deg = temp_list[i];
			deg_dist_x.append(temp_list[i]);
			deg_dist_y.append(1);
			num_deg = num_deg + 1;
	
	return deg_dist_x, deg_dist_y;

def normalize(list):
	res = [];
	low = min(list);
	high = max(list);
	for x in list:
		res.append(float(x-low)/(high-low));

	return res;

def complement(list):
	res = [];
	for x in list:
		res.append(1-x);

	return res;

#draw degree
for n in topo_08.graph0.nodes():
	degree = topo_08.node[n].indegree+len(topo_08.node[n].child);
	degree_list_08.append(degree);

'''
for n in topo_12.graph0.nodes():
	degree = topo_12.node[n].indegree+len(topo_12.node[n].child);
	degree_list_12.append(degree);
'''

for n in topo_16.graph0.nodes():
	degree = topo_16.node[n].indegree+len(topo_16.node[n].child);
	degree_list_16.append(degree);

deg_dist_x_08, deg_dist_y_08 = get_temp_list(degree_list_08);
#deg_dist_x_12, deg_dist_y_12 = get_temp_list(degree_list_12);
deg_dist_x_16, deg_dist_y_16 = get_temp_list(degree_list_16);

#draw deg distribution.
plt.figure(figsize=(8,8));
plt.yscale('log');
plt.xscale('log');

plt.plot( deg_dist_x_08, complement(normalize(np.cumsum(deg_dist_y_08))) , 'r--', label="CAIDA08");
#plt.plot( deg_dist_x_12, complement(normalize(np.cumsum(deg_dist_y_12))) , 'g-.', label="CAIDA12");
plt.plot( deg_dist_x_16, complement(normalize(np.cumsum(deg_dist_y_16))) , 'b', label="CAIDA16");
plt.ylabel("Degree Complement Cumulative Distribution Function");
plt.xlabel("Degree");
plt.legend();
plt.savefig("thesis_deg_dist.png");

#draw length.
plt.figure(figsize=(8,8));

plt.plot([ i for i in range( 1,len(topo_08.path_len_dist)+1 ) ], topo_08.path_len_dist, 'r--', label="CAIDA08");
#plt.plot([ i for i in range( 1,len(topo_12.path_len_dist)+1 ) ], topo_12.path_len_dist, 'g-.', label="CAIDA12");
plt.plot([ i for i in range( 1,len(topo_16.path_len_dist)+1 ) ], topo_16.path_len_dist, 'b', label="CAIDA16");
plt.ylabel("Path Length Distribution");
plt.xlabel("Path Length");
plt.legend();
plt.savefig("thesis_length_dist.png");

#draw length.
plt.figure(figsize=(8,8));

plt.plot([ i for i in range( 1,len(topo_08.path_len_dist)+1 ) ], normalize(topo_08.path_len_dist), 'r--', label="CAIDA08");
#plt.plot([ i for i in range( 1,len(topo_12.path_len_dist)+1 ) ], normalize(topo_12.path_len_dist), 'g-.', label="CAIDA12");
plt.plot([ i for i in range( 1,len(topo_16.path_len_dist)+1 ) ], normalize(topo_16.path_len_dist), 'b', label="CAIDA16");
plt.ylabel("Path Length Probability Density");
plt.xlabel("Path Length");
plt.legend();
plt.savefig("thesis_length_density.png");

#draw knn.
topo_08.calc_deg();
topo_08.calc_knn();
#topo_12.calc_knn();
topo_08.calc_deg();
topo_16.calc_knn();

plt.figure(figsize=(8,8));
plt.yscale('log');
plt.xscale('log');

plt.plot(topo_08.knn.keys(), topo_08.knn.values(), 'rx', label="CAIDA08");
#plt.plot(topo_12.knn.keys(), topo_12.knn.values(), 'g+', label="CAIDA12");
plt.plot(topo_16.knn.keys(), topo_16.knn.values(), 'bo', label="CAIDA16");
plt.legend();
plt.savefig("thesis_knn.png");

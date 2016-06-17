import ip_topo
import caida
import iplane
import download_worker
import os
import sys
import re

def usage():
	print "ip_query.py <source> <type> <time> <node> <target>";
	print "            source:'caida' or 'iplane' or 'lg' or 'hit'";
	print "            type:'ip' or 'router'";
	print "            time:'YYYYMMDD'";
	print "            target:'topo' or 'deg' or 'path' or 'ttl' or 'map'";

def read_auth(account):
	ret = [];

	is_provided = False;
	for line in open("auth", 'r'):
		if (line=="\n"):
			continue;
		if (is_provided and len(re.findall("#",line)) ==0):
			ret.append(line.strip('\n'));
		elif(is_provided):
			break;

		if (len(re.findall("#"+account,line)) != 0):
			is_provided = True;
	return ret;

def main(argv):
	if (len(argv) != 6 and len(argv) != 7):
		usage();
		exit();
	
	source = argv[1];
	type = argv[2];
	time = argv[3];
	node = argv[4];
	target = argv[5];
	is_parse = "";
	if (len(argv) == 7):
		is_parse = argv[6];
	
	if (source == "caida" and type == "ip" and node != "all"):
		dir = "data/caida/ip/"+time+"/"+node+"/";
		file = source+"."+type+"."+time+"."+node+"."+target;
		raw_file = source+"."+type+"."+time+"."+node;
		if not os.path.exists(dir):
			os.makedirs(dir);
		
		if os.path.exists(dir+file):
			print "already exists";
			exit();
		elif not os.path.exists(dir+raw_file):	
			print "raw file does not exist, start downloading...";
			auth = read_auth("caida");
			if ( len(auth) != 2 ):
				print "auth failed";
				exit();

			url = caida.get_url("caida", time, node);
			if ( url == None):
				print "no such record found";
				exit();
	
			download_worker.download_caida_restricted_worker(url, dir, raw_file+".warts.gz", auth[0], auth[1]);
			print "finished downloading.";
			print "dumping...";
			os.system("gunzip -q "+dir+raw_file+".warts.gz");
			os.system("sc_analysis_dump "+dir+raw_file+".warts > "+dir+raw_file); 
			print "finished dumping.";

		if not is_parse == "not":
			print "building topo...";
			topo = ip_topo.topo_graph(ip_topo.get_src(dir+raw_file),True);
			topo.build(dir+raw_file,"caida",True,True);
			topo.disp_stats();
			print "generating map...";
			topo.generate_map();
			print "exporting map...";
			topo.export_map(dir+raw_file);
			print "exporting simplified topo...";
			topo.export_topo_simplified(dir+raw_file);
			print "exporting graphviz...";
			topo.export_graphviz(dir+raw_file);
			print "exporting degree...";
			topo.export_degree(dir+raw_file);
			print "exporting path tree...";
			topo.export_path_tree(dir+raw_file);
			print "exporting border...";
			topo.export_border_ip(dir+raw_file);

	elif (source == "caida" and type == "ip" and node == "all"):
		dir = "data/caida/ip/"+time+"/all/";
		file = source+"."+type+"."+time+".all."+target;
		if not os.path.exists(dir):
			os.makedirs(dir);
		
		if os.path.exists(dir+file):
			print "already exists";
			exit();
		else:
			url_list = caida.get_time_list("caida", time);
			for u in url_list:
				node = u.split('/')[9].split('.')[5];
				raw_file = source+"."+type+"."+time+"."+node;
				if not os.path.exists(dir+raw_file):
					print "raw file "+raw_file+" does not exist, start downloading...";
					auth = read_auth("caida");
					if ( len(auth) != 2 ):
						print "auth failed";
						exit();
		
					url = caida.get_url("caida", time, node);
					if ( url == None):
						print "no such record found";
	
					download_worker.download_caida_restricted_worker(url, dir, raw_file+".warts.gz", auth[0], auth[1]);
					print "finished downloading.";
					print "dumping...";
					os.system("gunzip -q "+dir+raw_file+".warts.gz");
					os.system("sc_analysis_dump "+dir+raw_file+".warts > "+dir+raw_file); 
					print "finished dumping.";

	elif (source == "iplane" and type == "ip"):
		dir = "data/iplane/ip/"+time+"/";
		file = source+"."+type+"."+time+"."+node+"."+target;
		raw_file = source+"."+type+"."+time;
		url = iplane.get_url("iplane", time);
		dir_out = url.split('/')[6].split('.')[0];

		if not os.path.exists(dir):
			os.makedirs(dir);
		
		if os.path.exists(dir+file):
			print "already exists";
			exit();
		if not os.path.exists(dir+raw_file+".tar.gz"):
			print "raw file does not exist, start downloading...";
			auth = read_auth("iplane");
			if ( len(auth) != 2 ):
				print "auth failed";
				exit();

			if ( url == None ):
				print "no such record found";
				exit();
	
			download_worker.download_iplane_restricted_worker(url, dir, raw_file+".tar.gz", auth[0], auth[1]);
			print "finished downloading.";
		
		if not os.path.exists(dir+dir_out):
			print "uncompressing ...";
			os.system("tar -zxvf "+dir+raw_file+".tar.gz"+" -C "+dir);

		if not os.path.exists(dir+raw_file+".ls"):
			os.system("ls "+dir+dir_out+" > "+dir+raw_file+".ls");
			f_ls = open(dir+raw_file+".ls");
	
			for line in f_ls.readlines():
				n = line.split('.',2)[2].strip('\n');
				out_file = raw_file+"."+n
				os.system("./readoutfile "+dir+dir_out+"/"+line.strip('\n')+" > "+dir+out_file);
				print ("./readoutfile "+dir+dir_out+"/"+line.strip('\n')+" > "+dir+out_file);
			
			f_ls.close();
			print "finished dumping.";
		
		is_included = False;
		f_ls = open(dir+raw_file+".ls");

		for line in f_ls.readlines():
			n = line.split('.',2)[2].strip('\n');
			if (n == node):
				is_included = True;
		f_ls.close();

		if(not is_included):
			print "no such record";
			exit();
		
		print "building topo...";
		topo = ip_topo.topo_graph(ip_topo.get_src_iplane(dir+raw_file+"."+node),True);
		topo.build(dir+raw_file+"."+node,"iplane",True,True);
		topo.disp_stats();
		print "generating map...";
		topo.generate_map();
		print "exporting map...";
		topo.export_map(dir+raw_file+"."+node);
		print "exporting simplified topo...";
		topo.export_topo_simplified(dir+raw_file+"."+node);
		print "exporting graphviz...";
		topo.export_graphviz(dir+raw_file+"."+node);
		print "exporting degree...";
		topo.export_degree(dir+raw_file+"."+node);
		print "exporting path tree...";
		topo.export_path_tree(dir+raw_file+"."+node);
		print "exporting border...";
		topo.export_border_ip(dir+raw_file);

if __name__ == "__main__":
	main(sys.argv);

import ip_topo
import caida
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
	print "the output file is data/type/time/source/node/<target>";

def read_auth(account):
	ret = [];

	is_provided = False;
	for line in open("auth", 'r'):
		if (is_provided and len(re.findall("#",line)) ==0):
			ret.append(line.strip('\n'));
		elif(is_provided):
			break;

		if (len(re.findall("#"+account,line)) != 0):
			is_provided = True;
	return ret;

def main(argv):
	if (len(argv) != 6):
		usage();
		exit();
	
	source = argv[1];
	type = argv[2];
	time = argv[3];
	node = argv[4];
	target = argv[5];
	
	if (source == "caida" and type == "ip"):
		dir = "data/caida/ip/"+time+"/"+node+"/";
		file = source+"."+type+"."+time+"."+node+"."+target;
		if not os.path.exists(dir):
			os.makedirs(dir);
		
		if not os.path.exists(dir+file):
			print "file does not exist, start downloading...";
			auth = read_auth("caida");
			if ( len(auth) != 2 ):
				print "auth failed";
				exit();

			url = caida.get_url("caida", time, node);
			if ( url == None):
				print "not found";
				exit();
	
			raw_file = source+"."+type+"."+time+"."+node;
			download_worker.download_caida_restricted_worker(url, dir, raw_file+".warts.gz", auth[0], auth[1]);
			print "finished downloading.";
			print "dumping...";
			os.system("gunzip "+dir+raw_file+".warts.gz");
			os.system("sc_analysis_dump "+dir+raw_file+".warts > "+dir+raw_file); 
			print "finished dumping.";

		print "building topo...";
		topo = ip_topo.topo_graph(ip_topo.get_src(dir+raw_file));
		topo.build(dir+raw_file);
		topo.disp_stats();
		print "generating map...";
		topo.generate_map();
		print "exporting map...";
		topo.export_map(dir+raw_file);


if __name__ == "__main__":
	main(sys.argv);

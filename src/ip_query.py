import ip_topo

def usage():
	print "ip_query.py <source> <type> <time> <node> <target>";
	print "            type:'ip' or 'router'";
	print "            time:'YYYYMMDD'";
	print "            source:'caida' or 'iplane' or 'lg' or 'hit'";
	print "            target:'topo' or 'deg' or 'path' or 'ttl' or 'map'";
	print "the output file is data/type/time/source/node/<target>";

def main(argv):
	if (len(argv) != 5):
		usage();
	
	

import sys
import re

def get_src(file_name):
	f = open(file_name,'r');
	for line in f.readlines():
		if re.findall("#",line):
			continue;
		list = line.strip().split('\t');
		src = list[1];
		f.close();
		return src;

def parse_hop(hop):
	res = ["*","*","*"];
	if hop == "q":
		return res;

	list = hop.split(';');
	for e in list:
		tuple = e.split(',');
		i = int(tuple[2])-1;
		while i < 3:
			res[i] = tuple[0]+","+tuple[1];
			i = i + 1;
	return res;

def parse_trace(trace):
	if re.findall("#",trace):
		return False;
	list = trace.strip().split('\t');
	i = 13;
	while i < len(list):
		print parse_hop(list[i]);
		i = i + 1;
	return True;

def main(argv):
	if len(argv) != 2:
		print "usage:python analyze.py <dump_file_name>";
		return;
	f = open(argv[1], 'r');
	for line in f.readlines():
		if parse_trace(line):
			print "---------------------";

if __name__ == "__main__":
	main(sys.argv);

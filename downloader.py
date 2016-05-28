import urllib
import HTMLParser
import cookielib
import urllib2
import os
import time
import sys
from multiprocessing import Pool

#html parsers.
class CaidaParser(HTMLParser.HTMLParser):
	def __init__(self):
		HTMLParser.HTMLParser.__init__(self);
		self.img_cnt=0;
		self.alt="";
		self.file=[];
		self.dir=[];

	def get_attr_value(self, target, attrs):
		for e in attrs:
			key = e[0];
			value = e[1];
			if (key == target):
				return value;

	def handle_starttag(self, tag, attrs):
		if (tag == "img"):
			if (self.img_cnt >=2):
				alt_value = self.get_attr_value("alt", attrs);
				self.alt=alt_value;
			self.img_cnt = self.img_cnt + 1;
		
		if (tag == "a" and self.alt == "[DIR]"):
			href_value = self.get_attr_value("href", attrs);
			self.dir.append(href_value);
		elif (tag == "a" and self.alt != ""):
			href_value = self.get_attr_value("href", attrs);
			self.file.append(href_value);

class iPlaneParser(HTMLParser.HTMLParser):
	def __init__(self):
		HTMLParser.HTMLParser.__init__(self);
		self.img_cnt=0;
		self.alt="";
		self.file=[];
		self.dir=[];

	def get_attr_value(self, target, attrs):
		for e in attrs:
			key = e[0];
			value = e[1];
			if (key == target):
				return value;

	def handle_starttag(self, tag, attrs):
		if (tag == "img"):
			if (self.img_cnt >=2):
				alt_value = self.get_attr_value("alt", attrs);
				self.alt=alt_value;
			self.img_cnt = self.img_cnt + 1;
		
		if (tag == "a" and self.alt == "[DIR]"):
			href_value = self.get_attr_value("href", attrs);
			self.dir.append(href_value);
		elif (tag == "a" and self.alt != ""):
			href_value = self.get_attr_value("href", attrs);
			self.file.append(href_value);

#caida.
def download_caida(dir, file, url, root):
	os.chdir(root+dir);
	if not os.path.exists(root+dir+file):
		urllib.urlretrieve(url, root+dir+file);


def recursive_download_dir_caida(seed, depth, dir, root):
	if not os.path.exists(root):
		os.mkdir(root);
	f = urllib.urlopen(seed+dir);
	text = f.read();

	parser = CaidaParser();
	parser.feed(text);
	
	p = Pool(5);
	
	for e in parser.file:
		for i in range(depth):
			print "--",
		print e;
		#p.apply_async(download_caida, args=(dir, e, seed+dir+e, root, ));
		download_caida(dir, e, seed+dir+e, root);
		
	p.close();
	p.join();
	
	for e in parser.dir:
		for i in range(depth):
			print "--",
		print e;
		if not os.path.exists(root+e):
			os.mkdir(root+dir+e);

		recursive_download_dir_caida(seed, depth+1, dir+e, root);

#caida restricted.
def download_caida_restricted_worker(dir, file, url, root, opener):
	os.chdir(root+dir);
	CHUNK = 16*1024;
	if not os.path.exists(root+dir+file):
		f = opener.open(url);
		fp = open(file, 'wb');
		while True:
			chunk = f.read(CHUNK);
			if not chunk:
				break;
			fp.write(chunk);
	
	fp.close();

def download_caida_restricted(seed, depth, dir, root):
	username = "15b903031@hit.edu.cn";
	password = "yuzhuoxun123";
	
	passwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm();
	passwd_mgr.add_password("topo-data", seed, username, password);

	opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(passwd_mgr));
	recursive_download_dir_caida_restricted(seed, depth, dir, root, opener);

def recursive_download_dir_caida_restricted(seed, depth, dir, root, opener):
	if not os.path.exists(root):
		os.mkdir(root);
	f = opener.open(seed+dir);
	text = f.read();

	parser = CaidaParser();
	parser.feed(text);
	
	p = Pool(5);
	
	for e in parser.file:
		for i in range(depth):
			print "--",
		print e;
		#p.apply_async(download_caida_restricted_worker, args=(dir, e, seed+dir+e, root, opener, ));
		download_caida_restricted_worker(dir, e, seed+dir+e, root, opener);
		
	p.close();
	p.join();
	
	for e in parser.dir:
		for i in range(depth):
			print "--",
		print e;
		if not os.path.exists(root+e):
			os.mkdir(root+dir+e);

		recursive_download_dir_caida_restricted(seed, depth+1, dir+e, root);

#iplane.
def download_iplane_worker(dir, file, url, root, opener):
	os.chdir(root+dir);
	CHUNK = 16*1024;
	if not os.path.exists(root+dir+file):
		f = opener.open(url);
		fp = open(file, 'wb');
		while True:
			chunk = f.read(CHUNK);
			if not chunk:
				break;
			fp.write(chunk);
	
	fp.close();

def download_iplane(seed, depth, dir, root):
	print "loggin in...";
	username = "johnsonyuehit@163.com";
	password = "johnsonyue123";
	params = { "username": username, "password": password }; 
	
	cj = cookielib.CookieJar();
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj));
	urllib2.install_opener(opener);

	login_url = "https://access.ripe.net/?originalUrl=https%3A%2F%2Fdata-store.ripe.net%2Fdatasets%2Fiplane-traceroutes%2F&service=datarepo";
	post_data = urllib.urlencode(params).encode('utf-8');

	opener.open(login_url, post_data);
	print "done.";

	recursive_download_dir_iplane(seed, depth, dir, root, opener);

def recursive_download_dir_iplane(seed, depth, dir, root, opener):
	if not os.path.exists(root):
		os.mkdir(root);
	
	#start parsing.
	f = opener.open(seed+dir);
	text = f.read();

	parser = iPlaneParser();
	parser.feed(text);
	
	p = Pool(5);
	
	for e in parser.file:
		for i in range(depth):
			print "--",
		print e;
		#p.apply_async(download_iplane_worker, args=(dir, e, seed+dir+e, root, opener, ));
		download_iplane_worker(dir, e, seed+dir+e, root, opener);
	
	p.close();
	p.join();
	
	for e in parser.dir:
		for i in range(depth):
			print "--",
		print e;
		if not os.path.exists(root+e):
			os.mkdir(root+dir+e);

		recursive_download_dir_iplane(seed, depth+1, dir+e, root, opener)

def main(argv):
	#seed = "http://data.caida.org/datasets/topology/ark/ipv4/probe-data/team-2/2014/cycle-20140403/";
	#recursive_download_dir_caida(seed, 0, "", "/home/john/data/caida");
		
	#seed = "http://data-store.ripe.net/datasets/iplane-traceroutes/";
	#download_iplane(seed, 0, "", "/home/john/data/iplane/");

	seed = "https://topo-data.caida.org/ITDK/ITDK-2016-03/";
	download_caida_restricted(seed, 0, "", "/home/john/data/caida_restricted/");

if __name__ == "__main__":
	main(sys.argv);

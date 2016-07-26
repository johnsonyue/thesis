import HTMLParser
import urllib2
import re
import os

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

def get_caida_tree(dir, username, password):
	passwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm();
	passwd_mgr.add_password("topo-data", url, username, password);

	url = "https://topo-data.caida.org/team-probing/list-7.allpref24/";
	file = open("caida",'wb');
	opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(passwd_mgr));
	team_dir = ["team-1/daily/", "team-2/daily/", "team-3/daily/"]; 

	for t in team_dir:
		f = opener.open(url+t);
		text = f.read();
		parser = CaidaParser();
		parser.feed(text);
		
		team = t.split('/')[0];
	
		for e in parser.dir:
			get_year_dir(url+t+e, dir+team+"/", opener, file);
	
	file.close();

def get_year_dir(url, dir, opener, file):
	f = opener.open(url);
	text = f.read();
	
	parser = CaidaParser();
	parser.feed(text);

	for e in parser.dir:
		time = e.split('-')[1];
		get_time_dir(url+e, dir, opener, file);

def get_time_dir(url, dir, opener, file):
	f = opener.open(url);
	text = f.read();
	
	parser = CaidaParser();
	parser.feed(text);

	for e in parser.file:
		if ( len(e.split('.')) != 8 ):
			continue;
		time = e.split('.')[4];
		node = e.split('.')[5];
		node_dir = dir+time+"/"+node+"/";
		file.write(node_dir+":"+url+e+'\n');
		print node_dir;

def get_url(list_file_name, time, node):
	str = time+"/"+node;
	target = "";
	
	is_included = False;
	for line in open(list_file_name, 'r'):
		if (len(re.findall(str,line)) != 0):
			is_included = True;
			target = line;
			break;
	
	if (not is_included):
		return None;

	url = target.split(':', 1)[1];
	url = url.strip('\n');
	return url;

def get_time_list(list_file_name, time):
	str = time;
	target = "";
	res = [];
	
	is_included = False;
	for line in open(list_file_name, 'r'):
		if (len(re.findall(str,line)) != 0):
			is_included = True;
			target = line;
			url = target.split(':', 1)[1];
			url = url.strip('\n');
			res.append(url);
	
	if (not is_included):
		return None;

	return res;

#must be of the same length.
def time_cmp(t1, t2):
	for i in range(len(t1)):
		if (t1[i] != t2[i]):
			break;
	if (i < len(t1)):
		return int(t1[i]) - int(t2[i]);
	return 0;

def update_caida_tree(file_name, dir, username, password):
	f = open(file_name, 'rb');
	old_time = "00000000";
	for line in f.readlines():
		time = line.split('/')[-2].split('-')[1];
		if (time_cmp(time ,old_time) > 0):
			old_time = time;
	f.close();

	url = "https://topo-data.caida.org/team-probing/list-7.allpref24/";
	passwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm();
	passwd_mgr.add_password("topo-data", url, username, password);

	file = open("caida",'a');
	opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(passwd_mgr));
	team_dir = ["team-1/daily/", "team-2/daily/", "team-3/daily/"]; 

	for t in team_dir:
		f = opener.open(url+t);
		text = f.read();
		parser = CaidaParser();
		parser.feed(text);
		
		team = t.split('/')[0];
		old_year = old_time[:4];
	
		for e in parser.dir:
			if(time_cmp(e.strip('/'), old_year) >= 0):
				update_year_dir(old_time, url+t+e, dir+team+"/", opener, file);
	
	file.close();

	return "";

def update_year_dir(old_time, url, dir, opener, file):
	f = opener.open(url);
	text = f.read();
	
	parser = CaidaParser();
	parser.feed(text);

	for e in parser.dir:
		time = e.split('-')[1].strip('/');
		if (time_cmp(time, old_time) > 0):
			update_time_dir(url+e, dir, opener, file);

	return "";

def update_time_dir(url, dir, opener, file):
	f = opener.open(url);
	text = f.read();
	
	parser = CaidaParser();
	parser.feed(text);

	for e in parser.file:
		if ( len(e.split('.')) != 8 ):
			continue;
		time = e.split('.')[4];
		node = e.split('.')[5];
		node_dir = dir+time+"/"+node+"/";
		file.write(node_dir+":"+url+e+'\n');
		print node_dir;

update_caida_tree("caida", "", "15b903031@hit.edu.cn", "yuzhuoxun123");

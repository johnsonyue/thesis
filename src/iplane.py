import HTMLParser
import urllib
import urllib2
import re
import os
import cookielib

#html parsers.
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

def get_iplane_tree(dir, username, password):
	url = "https://data-store.ripe.net/datasets/iplane-traceroutes/";
		
	print "logging in...";
	params = { "username": username, "password": password }; 
	cj = cookielib.CookieJar();
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj));

	login_url = "https://access.ripe.net/?originalUrl=https%3A%2F%2Fdata-store.ripe.net%2Fdatasets%2Fiplane-traceroutes%2F&service=datarepo";
	post_data = urllib.urlencode(params).encode('utf-8');

	opener.open(login_url, post_data);
	print "done.";

	f = opener.open(url);
	text = f.read();

	parser = iPlaneParser();
	parser.feed(text);

	file = open("iplane",'wb');
	for e in parser.dir:
		get_year_dir(url+e, dir, opener, file);
	
	file.close();

def get_year_dir(url, dir, opener, file):
	f = opener.open(url);
	text = f.read();
	
	parser = iPlaneParser();
	parser.feed(text);

	for e in parser.file:
		list = e.split('_');
		time = list[1]+list[2]+list[3].split('.')[0];
		file.write(time+":"+url+e+"\n");

def get_url(list_file_name, time):
	target = "";
	
	is_included = False;
	for line in open(list_file_name, 'r'):
		if (len(re.findall(time,line)) != 0):
			is_included = True;
			target = line;
			break;
	
	if (not is_included):
		return None;

	url = target.split(':', 1)[1];
	url = url.strip('\n');
	return url;

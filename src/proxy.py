import HTMLParser
import urllib2

import sys
reload(sys);
sys.setdefaultencoding('utf-8');

#proxy parser for www.xicidaili.com.
class ProxyParser(HTMLParser.HTMLParser):
	def __init__(self, is_calc_page=False):
		HTMLParser.HTMLParser.__init__(self);
		
		self.is_calc_page=is_calc_page;
		self.is_pagination=False;
		self.is_page=False;
		self.page_num=[];
				
		self.tr_cnt=0;
		self.td_cnt=0;
		self.is_ip=False;
		self.is_port=False;
		self.is_uptime=False;
		self.ip=[];
		self.port=[];
		self.uptime=[];

	def get_attr_value(self, target, attrs):
		for e in attrs:
			key = e[0];
			value = e[1];
			if (key == target):
				return value;

	def handle_starttag(self, tag, attrs):
		if (self.is_calc_page):
			if (tag == "div" and self.get_attr_value("class",attrs) == "pagination"):
				self.is_pagination = True;
			elif(tag == "div"):
				self.is_pagination = False;
			if (self.is_pagination and tag == "a"):
				self.is_page = True;
		
		if (tag == "tr" and self.tr_cnt < 1):
			self.tr_cnt = self.tr_cnt + 1;
		
		if (tag == "td" and self.tr_cnt >= 1):
			if (self.td_cnt == 1):
				self.is_ip = True;
			elif (self.td_cnt == 2):
				self.is_port = True;
			elif (self.td_cnt == 8):
				self.is_uptime = True;
			self.td_cnt = self.td_cnt + 1;
		
		if ( self.td_cnt == 10):
			self.td_cnt = 0;
		
	def handle_data(self, data):
		if (self.is_ip):
			self.ip.append(data);
			self.is_ip = False;
		elif (self.is_port):
			self.port.append(data);
			self.is_port = False;
		elif (self.is_uptime):
			self.uptime.append(data.decode('utf-8'));
			self.is_uptime = False;
		elif (self.is_calc_page and self.is_page):
			ustr = data.decode('utf-8');
			if (ustr[0] >= u"\u0030" and ustr[0] <= u"\u0039"):
				self.page_num.append(int(ustr.encode('ascii')));
			self.is_page = False;

class ProxyPool():
	def __init__(self):
		self.seed_url = "http://www.xicidaili.com/nt/";
		self.parser = ProxyParser();
		request = urllib2.Request(self.seed_url);
		request.add_header('User-agent','Mozilla/5.0');
		f = urllib2.urlopen(request);
		text = f.read();
		self.parser.feed(text);
	
	def translate_uptime(self, uptime):
		num = u"";
		unit = u"";
		for i in range(len(uptime)):
			if (uptime[i] >= u"\u0030" and uptime[i] <= u"\u0039"):
				num = num + uptime[i];
			else:
				unit = unit + uptime[i];
		return num, unit;
	
	def get_candidate_proxy(self):
		res = [];
		for i in range(len(self.parser.ip)):
			num, unit = self.translate_uptime(self.parser.uptime[i]);
			if (int(num.encode('ascii')) >= 10 and unit == u"\u5929"):
				res.append(self.parser.ip[i]+":"+self.parser.port[i]);
		return res;
	
	def get_usable_proxy(self, list):
		return "";

pool = ProxyPool();
print pool.get_candidate_proxy();
parser = ProxyParser(True);
seed_url = "http://www.xicidaili.com/nt/";
request = urllib2.Request(seed_url);
request.add_header('User-agent','Mozilla/5.0');
f = urllib2.urlopen(request);
text = f.read();
parser.feed(text);
print parser.page_num;

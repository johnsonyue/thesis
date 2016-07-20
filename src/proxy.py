import HTMLParser
import urllib2
import socket
from multiprocessing import Pool

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
	def __init__(self, file=""):
		self.seed_url = "http://www.xicidaili.com/nt/";
		self.test_url = "http://data.caida.org/datasets/topology/ark/";
		self.proxy_list = [];
		self.ip_dict = {};
		if (file != ""):
			f = open(file);
			i = 0;
			for line in f.readlines():
				svr = line.strip('\n');
				self.proxy_list.append(svr);
				self.ip_dict[svr] = i;
				i = i + 1;
			
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
	
	def test_proxy(self, server):
		proxy = "http://"+server;
		opener = urllib2.build_opener(urllib2.ProxyHandler({"http":proxy}));
		code = 0;
		res = False;
		try:
			code = opener.open(self.test_url, timeout = 5).getcode();
		except urllib2.HTTPError ,e:
			res = False;
		except urllib2.URLError, e:
			res = False;
		except socket.timeout, e:
			res = False;
		except socket.error, e:
			res = False;

		if (code == 200):
			res = True;
		
		if (res_list != None and res_ind != -1):
			res_list[res_ind] = res;
		
		print (server+" "+str(res));

		return res;
		
	
	def test_list(self, svr_list, mp_num=1):
		ret = [];
		if (mp_num > 1):
			p = Pool(mp_num);
			res_list = [False for i in range(len(svr_list))];

			for i in range(len(svr_list)):
				svr = svr_list[i];
				res = p.apply_async(self.test_proxy, args=(svr, ));
				if (res):
					ret.append(svr);

			p.close();
			p.join();
		
		elif(mp_num == 1):
			for i in range(len(svr_list)):
				svr = svr_list[i];
				if (self.test_proxy(svr)):
					ret.append(svr);
		
		return ret;
	
	def update_proxy(self, check_legacy = False, max_page_num = 0, mp_num = 1):
		#updating legacy list.
		if (check_legacy):
			print "legacy list";
			self.proxy_list = self.test_list(self.proxy_list, mp_num);
			self.ip_dict = {};
			for i in range(len(self.proxy_list)):
				svr = self.proxy_list[i];
				self.ip_dict[svr] = i;
			print "legacy list finished testing.";

		#updating from xici.com.
		total_page = 1;
		cur_page = 1;
		while(cur_page <= total_page):
			print "page #"+str(cur_page);
			if (cur_page == 1):
				self.parser = ProxyParser(True);
				url = self.seed_url;
			else:
				self.parser = ProxyParser();
				url = self.seed_url+"/"+str(cur_page);
			#added user agent segment to avoid http 500 error.
			request = urllib2.Request(url);
			request.add_header('User-agent','Mozilla/5.0');
			f = urllib2.urlopen(request);
			text = f.read();
			self.parser.feed(text);
			if (cur_page == 1 and max_page_num <= 0):
				total_page = self.parser.page_num[-1];
			elif (cur_page == 1):
				total_page = max_page_num;

			svr_list = self.get_candidate_proxy();
			res_list = self.test_list(svr_list, mp_num);
			
			#adding to proxy_list.
			for i in range(len(res_list)):
				svr = res_list[i];
				if (not self.ip_dict.has_key(svr)):
					self.proxy_list.append(svr);
					self.ip_dict[svr] = len(self.proxy_list)-1;

			print "page #"+str(cur_page)+" finished testing,"+str(len(res_list))+"/"+str(len(svr_list))+" true.";
			print "total usable proxy ip num: "+str(len(self.proxy_list));

			cur_page = cur_page + 1;
						
	
	def export_proxy(self, file_name):
		f = open(file_name, 'wb');
		for svr in self.proxy_list:
			f.write(svr+'\n');
		f.close();
		
pool = ProxyPool("proxy_list");
pool.update_proxy(False, 400, 4);
pool.export_proxy("proxy_list");

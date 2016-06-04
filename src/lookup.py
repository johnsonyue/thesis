import urllib;
import os;
import json;

class lookup:
	def __init__(self):
		self.dir = "lookup/";
		self.cnt = 0;
		self.asn2cc = {};
		self.sorted = [];
		
		self.rir_url_list=[
			"http://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest",
			"http://ftp.apnic.net/pub/stats/apnic/delegated-apnic-latest",
			"http://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest",
			"http://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest",
			"http://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest"
		];
		self.bgp_url="http://data.caida.org/datasets/routing/routeviews-prefix2as/2016/06/routeviews-rv2-20160601-1200.pfx2as.gz";

		self.ip_bst = {'0':{}};
		
		self.get_pfx2asn();
		self.get_asn2cc();


	#asn => cc.
	def get_asn2cc(self):
		print ("building asn2cc ...");
		if not os.path.exists(self.dir):
			os.makedirs(self.dir);

		out_file = "asn2cc";
		if not os.path.exists(self.dir+out_file):
			for url in self.rir_url_list:
				file = url.split('/')[6];
				file = file.split('-')[1];
				if not os.path.exists(self.dir+file):
					urllib.urlretrieve(url, self.dir+file);
				
				f = open(self.dir+file);
				self.cnt = 0;
				for line in f.readlines():
					self.parse_asn_line(line);
				f.close();
				print (file+" parsed");
			
				self.sorted = sorted(self.asn2cc.iteritems(), key=lambda d:int(d[0]));
				f = open(self.dir+out_file, 'wb');
				for t in self.sorted:
					f.write(t[0]+"|"+t[1]+'\n');
				f.close();
		else:
			f = open(self.dir+out_file);
			for line in f.readlines():
				list = line.split('|');
				self.asn2cc[list[0]] = list[1].strip('\n');
			f.close();
	
	def parse_asn_line(self, line):
		if (line[0] == '#'):
			return;
		if (self.cnt < 4):
			self.cnt = self.cnt + 1;
			return;
		
		list = line.split('|');
		type = list[2];
		if (type == "asn"):
			cc = list[1];
			if (cc == ""):
				return;
			asn = int(list[3]);
			value = int(list[4]);
			for i in range(value):
				key = asn+i;
				self.asn2cc[str(key)] = cc;

	#pfx => asn.
	def byte2bin(self, dec):
		result = [];
		for i in range(8):
			result.append(0);
		
		for i in range(8):
			result[i] = dec % 2;
			dec = dec / 2;
		
		result.reverse();
		return result;

	def pfx2bin(self, pfx, msk):
		bin = [];
		list = pfx.split('.');
		
		for i in range(len(list)):
			if(msk <= 0):
				break;
			bits = (8 if msk/8 else msk%8);
			byte =  self.byte2bin(int(list[i]));
			bin.extend(byte[:bits]);
			msk = msk - bits;
		
		return bin;
	
	def parse_pfx_line(self, line):
		list = line.split('\t');
		class_a = list[0].split('.')[0];
		bin = self.pfx2bin(list[0].split('.',1)[1], int(list[1])-8);
		
		if (not self.ip_bst.has_key(class_a)):
			self.ip_bst[class_a] = {};

		ptr = self.ip_bst[class_a];
		for b in bin:
			if not ptr.has_key(b):
				ptr[b] = {};
			ptr = ptr[b];
		
		ptr["asn"] = list[2].strip('\n');
	
	
	def get_pfx2asn(self):
		print "building pfx2asn ...";
		if not os.path.exists(self.dir):
			os.makedirs(self.dir);
		
		out_file = "ip_bst";
		if not os.path.exists(self.dir+out_file):
			file = "pfx2asn";
			if not os.path.exists(self.dir+file):
				print "downloading "+self.bgp_url+" ...";
				urllib.urlretrieve(self.bgp_url, self.dir+file+".gz");
				os.system("gunzip "+self.dir+file+".gz");
				print "downloaded.";
			
			print "parsing "+file+" ...";
			f = open(self.dir+file);
			for line in f.readlines():
				self.parse_pfx_line(line);
			f.close();
			print "parsed.";
			
			f = open(self.dir+out_file,'wb');
			f.write(json.dumps(self.ip_bst));
			f.close();
		else:
			f = open(self.dir+out_file);
			self.ip_bst = json.loads(f.read());
			f.close();
		
	#retriever.
	def get_asn_from_pfx(self, ip):
		class_a = ip.split('.')[0];
		bin = self.pfx2bin(ip.split('.',1)[1], 24);
		result = [];

		ptr = self.ip_bst[class_a];
		for b in bin:
			if (ptr.has_key("asn")):
				result.append(ptr["asn"]);
			if (ptr.has_key(b)):
				ptr = ptr[b];
			elif (ptr.has_key(str(b))):
				ptr = ptr[str(b)];
			else:
				break;
		
		if (len(result) == 0):
			return None;
		else:
			return result[len(result)-1];
	
	def get_cc_from_asn(self, asn):
		if not asn:
			return "*";
		asn = asn.split('_')[0];
		asn = asn.split(',')[0];
		if not self.asn2cc.has_key(asn):
			return "*";
		
		return self.asn2cc[asn];

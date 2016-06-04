import urllib
import urllib2
import os
import cookielib

#caida restricted.
def download_caida_restricted_worker(url, dir, file, username, password):
	passwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm();
	passwd_mgr.add_password("topo-data", url, username, password);

	opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(passwd_mgr));

	if not os.path.exists(dir):
		os.makedirs(dir);

	CHUNK = 16*1024;
	if not os.path.exists(dir+file):
		f = opener.open(url);
		fp = open(dir+file, 'wb');
		while True:
			chunk = f.read(CHUNK);
			if not chunk:
				break;
			fp.write(chunk);
		fp.close();

def download_iplane_restricted_worker(url, dir, file, username, password):
	print "logging in...";
	login_url = "https://access.ripe.net/?originalUrl=https%3A%2F%2Fdata-store.ripe.net%2Fdatasets%2Fiplane-traceroutes%2F&service=datarepo";
	params = { "username": username, "password": password }; 
	cj = cookielib.CookieJar();
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj));

	post_data = urllib.urlencode(params).encode('utf-8');

	opener.open(login_url, post_data);
	print "done.";
	
	if not os.path.exists(dir):
		os.makedirs(dir);

	CHUNK = 16*1024;
	if not os.path.exists(dir+file):
		f = opener.open(url);
		fp = open(dir+file, 'wb');
		while True:
			chunk = f.read(CHUNK);
			if not chunk:
				break;
			fp.write(chunk);
		fp.close();


def download_irr_delegate(url_list, dir, file):
	if not os.path.exists(root+dir+file):
		urllib.urlretrieve(url, root+dir+file);

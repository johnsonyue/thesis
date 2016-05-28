import urllib2
import os

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

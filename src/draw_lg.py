import ip_topo

topo = ip_topo.topo_graph(ip_topo.get_src_lg(),False);
topo.build("traces.txt","lg",False,False);
topo.calc_deg();
topo.calc_knn();
topo.draw_deg("lg");
topo.draw_knn("lg");
topo.draw_path("lg");

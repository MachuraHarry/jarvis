import gi,sys; gi.require_version('Gdk','3.0'); from gi.repository import Gdk
w=Gdk.get_default_root_window(); pb=Gdk.pixbuf_get_from_window(w,0,0,w.get_width(),w.get_height())
pb=pb.scale_simple(w.get_width()//2,w.get_height()//2,2); pb.savev(sys.argv[1],'png',[],[])

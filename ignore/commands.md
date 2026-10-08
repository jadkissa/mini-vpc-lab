SSH Router : ssh jad@192.168.56.10
SSH Public VM via Router : ssh -J jad@192.168.56.10 jad@10.0.1.10
SSH Private VM via Router then Public VM : ssh -J jad@192.168.56.10,jad@10.0.1.10 jad@10.0.3.10
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub

# Import the TOTP engine created previously
from totp_engine import TOTPMTDEngine

class TOTPPeerToPeerController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TOTPPeerToPeerController, self).__init__(*args, **kwargs)
        
        # Initialize TOTP engine (30 seconds mutation interval for testing)
        self.mtd = TOTPMTDEngine(time_step_ms=30000)
        
        # Host configuration (Modify these IPs based on your Containernet setup)
        self.peer_a_ip = "10.0.0.1"  # Authorized Client (c1)
        self.peer_b_ip = "10.0.0.3"  # Target Server (Juice Shop - Verify this IP)
        self.service_port = 80       # The real port the service is listening on
        
        self.switches = {}
        # Start a thread to update flow rules every 30 seconds
        self.updater_thread = hub.spawn(self._update_loop)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.switches[datapath.id] = datapath
        # Default table-miss entry could be added here if not present by default

    def _update_loop(self):
        """Infinite loop that calculates new OTPs and pushes them to the switches."""
        while True:
            ports = self.mtd.get_active_window()
            self.logger.info("MTD Update - Active OTP Ports: %s", ports) # Log identifying the 3 active slots
            for datapath in self.switches.values():
                self.install_peer_to_peer_rules(datapath)
            
            # Wait for the next time slot before recalculating
            hub.sleep(self.mtd.time_step_ms / 1000.0)

    def install_peer_to_peer_rules(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # FIX: Usa il metodo corretto per ottenere le porte dal motore TOTP!
        ports = self.mtd.get_active_window()
        dpid = datapath.id

        # ==========================================
        # S2: EXTERNAL EDGE (Il Mutatore)
        # ==========================================
        if dpid == 2:
            # 1. OUTBOUND (Andata: c1 -> target): Nascondi la porta 80 mutandola in OTP
            match_req = parser.OFPMatch(eth_type=0x0800, ip_proto=6, 
                                        ipv4_src=self.peer_a_ip, ipv4_dst=self.peer_b_ip, 
                                        tcp_dst=self.service_port)
            actions_req = [parser.OFPActionSetField(tcp_dst=ports['current']), 
                           parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
            self.add_flow(datapath, 1100, match_req, actions_req, 101)

            # 2. INBOUND (Ritorno: target -> c1): Ripristina l'OTP mutato alla porta 80 originale
            for otp in ports.values():
                match_res = parser.OFPMatch(eth_type=0x0800, ip_proto=6, 
                                            ipv4_src=self.peer_b_ip, ipv4_dst=self.peer_a_ip, 
                                            tcp_src=otp)
                actions_res = [parser.OFPActionSetField(tcp_src=self.service_port), 
                               parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
                self.add_flow(datapath, 1100, match_res, actions_res, 101)

        # ==========================================
        # S3: INTERNAL EDGE (Il Ripristinatore e Firewall)
        # ==========================================
        elif dpid == 3:
            # 1. INBOUND (Andata: c1 -> target): Riconosci l'OTP e ripristina a porta 80 per il server
            for otp in ports.values():
                match_req = parser.OFPMatch(eth_type=0x0800, ip_proto=6, 
                                            ipv4_src=self.peer_a_ip, ipv4_dst=self.peer_b_ip, 
                                            tcp_dst=otp)
                actions_req = [parser.OFPActionSetField(tcp_dst=self.service_port), 
                               parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
                self.add_flow(datapath, 1100, match_req, actions_req, 101)

            # 2. OUTBOUND (Ritorno: target -> c1): Nascondi la risposta della porta 80 mutandola in OTP
            match_res = parser.OFPMatch(eth_type=0x0800, ip_proto=6, 
                                        ipv4_src=self.peer_b_ip, ipv4_dst=self.peer_a_ip, 
                                        tcp_src=self.service_port)
            actions_res = [parser.OFPActionSetField(tcp_src=ports['current']), 
                           parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
            self.add_flow(datapath, 1100, match_res, actions_res, 101)

            # 3. FIREWALL STEALTH (Blocca l'attaccante a1 e gli scanner)
            # Qualsiasi pacchetto che cerchi di arrivare direttamente alla porta 80 viene scartato
            match_drop = parser.OFPMatch(eth_type=0x0800, ip_proto=6, 
                                         ipv4_dst=self.peer_b_ip, 
                                         tcp_dst=self.service_port)
            actions_drop = [] # Array vuoto = DROP in OpenFlow
            self.add_flow(datapath, 1000, match_drop, actions_drop, 101)

        # ==========================================
        # S1: CORE SWITCH
        # ==========================================
        elif dpid == 1:
            pass


    # --- STANDARD RYU HELPER FUNCTIONS ---
    def add_flow(self, datapath, priority, match, actions, cookie=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, cookie=cookie,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    def del_rules(self, datapath, cookie):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(datapath=datapath, cookie=cookie, cookie_mask=0xFFFFFFFFFFFFFFFF,
                                table_id=ofproto.OFPTT_ALL, command=ofproto.OFPFC_DELETE, 
                                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY)
        datapath.send_msg(mod)
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub

import config
from totp_engine import TOTPMTDEngine

class TOTPPeerToPeerController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TOTPPeerToPeerController, self).__init__(*args, **kwargs)
        
        # Initialize TOTP engine using variables from config.py
        self.mtd = TOTPMTDEngine(
            secret_key=config.SECRET_KEY, 
            time_step_ms=config.TIME_STEP_MS
        )
        
        # Host configuration loaded from config.py
        self.peer_a_ip = config.PEER_A_IP
        self.peer_b_ip = config.PEER_B_IP
        self.service_port = config.SERVICE_PORT
        
        self.switches = {}
        # Start a thread to update flow rules dynamically
        self.updater_thread = hub.spawn(self._update_loop)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.switches[datapath.id] = datapath

    def _update_loop(self):
        """Infinite loop that calculates new OTPs and pushes them to the switches."""
        while True:
            ports = self.mtd.get_active_window()
            # Log identifying the 3 active slots
            self.logger.info("MTD Update - Active OTP Ports: %s", ports) 
            for datapath in self.switches.values():
                self.install_peer_to_peer_rules(datapath)
            
            # Wait for the next time slot before recalculating
            hub.sleep(self.mtd.time_step_ms / 1000.0)

    def install_peer_to_peer_rules(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        ports = self.mtd.get_active_window()
        dpid = datapath.id

        # ==========================================
        # S2: EXTERNAL EDGE (The Mutator)
        # ==========================================
        if dpid == 2:
            # 1. OUTBOUND (Forward: c1 -> target): Hide port 80 by mutating it into the OTP
            match_req = parser.OFPMatch(eth_type=0x0800, ip_proto=6, 
                                        ipv4_src=self.peer_a_ip, ipv4_dst=self.peer_b_ip, 
                                        tcp_dst=self.service_port)
            actions_req = [parser.OFPActionSetField(tcp_dst=ports['current']), 
                           parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
            self.add_flow(datapath, 1100, match_req, actions_req, 101)

            # 2. INBOUND (Return: target -> c1): Restore the mutated OTP back to the original service port
            for otp in ports.values():
                match_res = parser.OFPMatch(eth_type=0x0800, ip_proto=6, 
                                            ipv4_src=self.peer_b_ip, ipv4_dst=self.peer_a_ip, 
                                            tcp_src=otp)
                actions_res = [parser.OFPActionSetField(tcp_src=self.service_port), 
                               parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
                self.add_flow(datapath, 1100, match_res, actions_res, 101)

        # ==========================================
        # S3: INTERNAL EDGE (The Restorer and Firewall)
        # ==========================================
        elif dpid == 3:
            # 1. INBOUND (Forward: c1 -> target): Recognize the OTP and restore to the service port for the server
            for otp in ports.values():
                match_req = parser.OFPMatch(eth_type=0x0800, ip_proto=6, 
                                            ipv4_src=self.peer_a_ip, ipv4_dst=self.peer_b_ip, 
                                            tcp_dst=otp)
                actions_req = [parser.OFPActionSetField(tcp_dst=self.service_port), 
                               parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
                self.add_flow(datapath, 1100, match_req, actions_req, 101)

            # 2. OUTBOUND (Return: target -> c1): Hide the service port response by mutating it into the OTP
            match_res = parser.OFPMatch(eth_type=0x0800, ip_proto=6, 
                                        ipv4_src=self.peer_b_ip, ipv4_dst=self.peer_a_ip, 
                                        tcp_src=self.service_port)
            actions_res = [parser.OFPActionSetField(tcp_src=ports['current']), 
                           parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
            self.add_flow(datapath, 1100, match_res, actions_res, 101)  

            # 3. STEALTH FIREWALL (Blocks unauthenticated attackers and scanners)
            # Any packet attempting to reach the service port directly is dropped
            match_drop = parser.OFPMatch(eth_type=0x0800, ip_proto=6, 
                                         ipv4_dst=self.peer_b_ip, 
                                         tcp_dst=self.service_port)
            actions_drop = [] # Empty array = DROP in OpenFlow
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
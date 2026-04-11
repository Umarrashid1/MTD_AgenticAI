# main_controller.py
import random
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import packet, ethernet, ipv4, arp, tcp, udp
from ryu.lib import hub

import config
from mtd_engine import MTDEngine

class ControllerMTD(app_manager.RyuApp):
    OFP_VERSIONS = [0x04]

    def __init__(self, *args, **kwargs):
        super(ControllerMTD, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.ip_to_mac = {}
        
        self.mtd_engine = MTDEngine()
        self.shuffling_thread = hub.spawn(self._shuffling_loop)

    # =========================================================================
    # CORE: THREADING & SHUFFLING
    # =========================================================================
    def _shuffling_loop(self):
        """ Background thread orchestrating the MTD mutations. """
        while True:
            interval = random.randint(config.SHUFFLE_MIN_TIME, config.SHUFFLE_MAX_TIME)
            hub.sleep(interval)
            
            # 1. Proactive Data Plane Cleanup
            if hasattr(self, 'target_datapath'):
                self._clear_mtd_flows(self.target_datapath)
                hub.sleep(1) 

            # 2. Mathematical Shuffling
            ip_map, port_map = self.mtd_engine.shuffle_all()
            
            self.logger.info("\n========== MTD SHUFFLE EXECUTED ==========")
            for r, v in ip_map.items():
                self.logger.info("[IP] Real %s -> Virtual %s", r, v)
            for (r_ip, r_port), v_port in port_map.items():
                self.logger.info("[PORT] %s:%s -> Port %s", r_ip, r_port, v_port)
            self.logger.info("==========================================\n")
                
            # 3. Network State Update
            self._send_garps_for_all()

    def _send_garps_for_all(self):
        """ Broadcast GARPs to update host ARP caches with new Virtual IPs. """
        if not hasattr(self, 'target_datapath'): return
        for r_ip, v_ip in self.mtd_engine.real_to_virtual_ip.items():
            mac = self.ip_to_mac.get(r_ip)
            if mac:
                self._send_gratuitous_arp(self.target_datapath, v_ip, mac)
                hub.sleep(0.2)

    # =========================================================================
    # OPENFLOW EVENT HANDLERS
    # =========================================================================
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """ Installs the fundamental Table-Miss flow entry. """
        self.target_datapath = ev.msg.datapath
        ofproto, parser = self.target_datapath.ofproto, self.target_datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(self.target_datapath, 0, match, actions)
        self.logger.info("--- MTD READY: Table-Miss Installed ---")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """ Core Packet processing engine (ARP Proxy & NAT Translation). """
        msg = ev.msg
        datapath = msg.datapath
        ofproto, parser = datapath.ofproto, datapath.ofproto_parser
        in_port = msg.match['in_port']
        
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if not eth: return

        # --- 1. ARP PROXY MANAGEMENT ---
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            self.ip_to_mac[pkt_arp.src_ip] = eth.src
            if pkt_arp.opcode == arp.ARP_REQUEST and self.mtd_engine.is_virtual_ip(pkt_arp.dst_ip):
                self._handle_arp(datapath, in_port, eth, pkt_arp)
                return

        # --- 2. IP & PORT NAT MANAGEMENT ---
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
        pkt_tcp = pkt.get_protocol(tcp.tcp)
        pkt_udp = pkt.get_protocol(udp.udp)
        
        actions = []
        
        if pkt_ipv4:
            self.ip_to_mac[pkt_ipv4.src] = eth.src
            
            # --- INBOUND NAT (Client to Server) ---
            if self.mtd_engine.is_virtual_ip(pkt_ipv4.dst):
                real_dst = self.mtd_engine.get_real_ip(pkt_ipv4.dst)
                actions.append(parser.OFPActionSetField(ipv4_dst=real_dst))
                
                # Port Translation (Inbound)
                if pkt_tcp:
                    real_port = self.mtd_engine.get_real_port(real_dst, pkt_tcp.dst_port)
                    if real_port:
                        actions.append(parser.OFPActionSetField(tcp_dst=real_port))
                        self.logger.info("MTD [IN-TCP]: Port %s -> %s", pkt_tcp.dst_port, real_port)
                elif pkt_udp:
                    real_port = self.mtd_engine.get_real_port(real_dst, pkt_udp.dst_port)
                    if real_port:
                        actions.append(parser.OFPActionSetField(udp_dst=real_port))
                        
                self.logger.info("MTD [IN-IP]: %s -> %s", pkt_ipv4.dst, real_dst)
                
            # --- OUTBOUND NAT (Server to Client) ---
            elif self.mtd_engine.is_real_ip(pkt_ipv4.src):
                virt_src = self.mtd_engine.get_virtual_ip(pkt_ipv4.src)
                actions.append(parser.OFPActionSetField(ipv4_src=virt_src))
                
                # Port Translation (Outbound)
                if pkt_tcp:
                    virt_port = self.mtd_engine.get_virtual_port(pkt_ipv4.src, pkt_tcp.src_port)
                    if virt_port:
                        actions.append(parser.OFPActionSetField(tcp_src=virt_port))
                        self.logger.info("MTD [OUT-TCP]: Port %s -> %s", pkt_tcp.src_port, virt_port)
                elif pkt_udp:
                    virt_port = self.mtd_engine.get_virtual_port(pkt_ipv4.src, pkt_udp.src_port)
                    if virt_port:
                        actions.append(parser.OFPActionSetField(udp_src=virt_port))
                        
                self.logger.info("MTD [OUT-IP]: %s -> %s", pkt_ipv4.src, virt_src)

        # --- 3. L2 FORWARDING ---
        self.mac_to_port.setdefault(datapath.id, {})
        self.mac_to_port[datapath.id][eth.src] = in_port
        out_port = self.mac_to_port[datapath.id].get(eth.dst, ofproto.OFPP_FLOOD)
        actions.append(parser.OFPActionOutput(out_port))

        # --- 4. HARDWARE OFFLOADING OPTIMIZATION ---
        if pkt_ipv4:
            # We must explicitly specify IP protocol if we match transport ports
            if pkt_tcp:
                match = parser.OFPMatch(in_port=in_port, eth_type=0x0800, ip_proto=6,
                                        ipv4_src=pkt_ipv4.src, ipv4_dst=pkt_ipv4.dst,
                                        tcp_src=pkt_tcp.src_port, tcp_dst=pkt_tcp.dst_port)
            elif pkt_udp:
                match = parser.OFPMatch(in_port=in_port, eth_type=0x0800, ip_proto=17,
                                        ipv4_src=pkt_ipv4.src, ipv4_dst=pkt_ipv4.dst,
                                        udp_src=pkt_udp.src_port, udp_dst=pkt_udp.dst_port)
            else:
                # ICMP (Ping) or other non-TCP/UDP traffic
                match = parser.OFPMatch(in_port=in_port, eth_type=0x0800,
                                        ipv4_src=pkt_ipv4.src, ipv4_dst=pkt_ipv4.dst)
            
            self.add_flow(datapath, 1, match, actions, idle_timeout=config.HARDWARE_IDLE_TIMEOUT)
            self.logger.info("+++ HW OFFLOAD INSTALLED +++")

        # Send current packet out
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, 
                                  data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None)
        datapath.send_msg(out)

    # =========================================================================
    # OPENFLOW MESSAGING HELPERS
    # =========================================================================
    def add_flow(self, datapath, priority, match, actions, idle_timeout=0):
        inst = [datapath.ofproto_parser.OFPInstructionActions(datapath.ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = datapath.ofproto_parser.OFPFlowMod(datapath=datapath, priority=priority, 
                                                 match=match, instructions=inst, idle_timeout=idle_timeout)
        datapath.send_msg(mod)

    def _clear_mtd_flows(self, datapath):
        parser, ofproto = datapath.ofproto_parser, datapath.ofproto
        mod_del = parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE, 
                                    out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY, match=parser.OFPMatch())
        datapath.send_msg(mod_del)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, parser.OFPMatch(), actions)

    def _handle_arp(self, datapath, in_port, eth, pkt_arp):
        real_ip = self.mtd_engine.get_real_ip(pkt_arp.dst_ip)
        target_mac = self.ip_to_mac.get(real_ip)
        if not target_mac: return
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=eth.ethertype, dst=eth.src, src=target_mac))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY, src_mac=target_mac, src_ip=pkt_arp.dst_ip, 
                                 dst_mac=eth.src, dst_ip=pkt_arp.src_ip))
        pkt.serialize()
        actions = [datapath.ofproto_parser.OFPActionOutput(in_port)]
        out = datapath.ofproto_parser.OFPPacketOut(datapath=datapath, buffer_id=0xffffffff, 
                                                   in_port=datapath.ofproto.OFPP_CONTROLLER, actions=actions, data=pkt.data)
        datapath.send_msg(out)

    def _send_gratuitous_arp(self, datapath, ip_virtuale, mac_reale):
        parser, ofproto = datapath.ofproto_parser, datapath.ofproto
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=0x0806, dst='ff:ff:ff:ff:ff:ff', src=mac_reale))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY, src_mac=mac_reale, src_ip=ip_virtuale, 
                                 dst_mac='ff:ff:ff:ff:ff:ff', dst_ip=ip_virtuale))
        pkt.serialize()
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, 
                                  in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=pkt.data)
        datapath.send_msg(out)
import random
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import packet, ethernet, ipv4, arp
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
        # Spawn a green thread to handle periodic IP shuffling
        self.shuffling_thread = hub.spawn(self._shuffling_loop)

    def _shuffling_loop(self):
        """ Periodically changes the Virtual IP mapping to confuse attackers """
        while True:
            # Wait for a random interval defined in config
            interval = random.randint(config.SHUFFLE_MIN_TIME, config.SHUFFLE_MAX_TIME)
            hub.sleep(interval)
            
            if hasattr(self, 'target_datapath'):
                # Flush old NAT rules before applying new mappings
                self._clear_mtd_flows(self.target_datapath)
                hub.sleep(1) 

            # Generate new Virtual IPs
            mapping = self.mtd_engine.shuffle_ips()
            self.logger.info("--- MTD SHUFFLE EXECUTED ---")
            for r, v in mapping.items():
                self.logger.info("Real Host %s -> Virtual IP %s", r, v)
                
            # Update all hosts in the network with the new Virtual IPs via ARP
            self._send_garps_for_all()

    def _send_garps_for_all(self):
        """ Sends Gratuitous ARP replies for all mapped hosts """
        if not hasattr(self, 'target_datapath'): return
        for r_ip, v_ip in self.mtd_engine.real_to_virtual.items():
            mac = self.ip_to_mac.get(r_ip)
            if mac:
                self._send_gratuitous_arp(self.target_datapath, v_ip, mac)
                hub.sleep(0.2)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """ Initial switch configuration: installs the table-miss flow entry """
        self.target_datapath = ev.msg.datapath
        ofproto, parser = self.target_datapath.ofproto, self.target_datapath.ofproto_parser
        
        # Match all packets and send them to the controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(self.target_datapath, 0, match, actions)
        self.logger.info("--- MTD READY: Table-Miss Installed ---")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """ Handles packets sent to the controller (Table-miss or MTD logic) """
        msg = ev.msg
        datapath = msg.datapath
        ofproto, parser = datapath.ofproto, datapath.ofproto_parser
        in_port = msg.match['in_port']
        
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if not eth: return

        # 1. ARP MANAGEMENT
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            # Learn IP-to-MAC mapping
            self.ip_to_mac[pkt_arp.src_ip] = eth.src
            # Proxy ARP: handle requests for Virtual IPs
            if pkt_arp.opcode == arp.ARP_REQUEST and self.mtd_engine.is_virtual_ip(pkt_arp.dst_ip):
                self._handle_arp(datapath, in_port, eth, pkt_arp)
                return

        # 2. IP MANAGEMENT + NAT (Network Address Translation)
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
        actions = []
        
        if pkt_ipv4:
            self.ip_to_mac[pkt_ipv4.src] = eth.src
            # INBOUND NAT: Virtual Destination -> Real Destination
            if self.mtd_engine.is_virtual_ip(pkt_ipv4.dst):
                real_dst = self.mtd_engine.get_real_ip(pkt_ipv4.dst)
                actions.append(parser.OFPActionSetField(ipv4_dst=real_dst))
                self.logger.info("MTD [IN]: Translation %s -> %s", pkt_ipv4.dst, real_dst)
            
            # OUTBOUND NAT: Real Source -> Virtual Source (Masking)
            elif self.mtd_engine.is_real_ip(pkt_ipv4.src):
                virt_src = self.mtd_engine.get_virtual_ip(pkt_ipv4.src)
                actions.append(parser.OFPActionSetField(ipv4_src=virt_src))
                self.logger.info("MTD [OUT]: Masking %s -> %s", pkt_ipv4.src, virt_src)

        # 3. FORWARDING AND HARDWARE OFFLOADING
        self.mac_to_port.setdefault(datapath.id, {})
        self.mac_to_port[datapath.id][eth.src] = in_port
        
        # Standard L2 learning/forwarding
        out_port = self.mac_to_port[datapath.id].get(eth.dst, ofproto.OFPP_FLOOD)
        actions.append(parser.OFPActionOutput(out_port))

        # OPTIMIZATION: Install a flow rule in the switch to avoid Packet-In for this stream
        if out_port != ofproto.OFPP_FLOOD:
            if pkt_ipv4:
                # Install temporary rule (idle_timeout) for the specific IP flow
                match = parser.OFPMatch(in_port=in_port, eth_type=0x0800, ipv4_src=pkt_ipv4.src, ipv4_dst=pkt_ipv4.dst)
                self.add_flow(datapath, 1, match, actions, idle_timeout=10)
                self.logger.info("+++ HW OFFLOAD: Rule installed for %s -> %s +++", pkt_ipv4.src, pkt_ipv4.dst)

        # Send the current packet out
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None)
        datapath.send_msg(out)

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0):
        """ Helper to add flow entries to the switch """
        inst = [datapath.ofproto_parser.OFPInstructionActions(datapath.ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = datapath.ofproto_parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst, idle_timeout=idle_timeout)
        datapath.send_msg(mod)

    def _clear_mtd_flows(self, datapath):
        """ Removes all flows to reset the NAT state during shuffling """
        parser, ofproto = datapath.ofproto_parser, datapath.ofproto
        # Delete all existing flows
        mod_del = parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE, out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY, match=parser.OFPMatch())
        datapath.send_msg(mod_del)
        # Re-install the default table-miss rule
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, parser.OFPMatch(), actions)

    def _handle_arp(self, datapath, in_port, eth, pkt_arp):
        """ Craft an ARP reply to map a Virtual IP to a Real MAC address """
        real_ip = self.mtd_engine.get_real_ip(pkt_arp.dst_ip)
        target_mac = self.ip_to_mac.get(real_ip)
        if not target_mac: return
        
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=eth.ethertype, dst=eth.src, src=target_mac))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY, src_mac=target_mac, src_ip=pkt_arp.dst_ip, dst_mac=eth.src, dst_ip=pkt_arp.src_ip))
        pkt.serialize()
        
        actions = [datapath.ofproto_parser.OFPActionOutput(in_port)]
        out = datapath.ofproto_parser.OFPPacketOut(datapath=datapath, buffer_id=0xffffffff, in_port=datapath.ofproto.OFPP_CONTROLLER, actions=actions, data=pkt.data)
        datapath.send_msg(out)

    def _send_gratuitous_arp(self, datapath, ip_virtuale, mac_reale):
        """ Broadcasts an ARP Reply to force host cache updates with new Virtual IP """
        parser, ofproto = datapath.ofproto_parser, datapath.ofproto
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=0x0806, dst='ff:ff:ff:ff:ff:ff', src=mac_reale))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY, src_mac=mac_reale, src_ip=ip_virtuale, dst_mac='ff:ff:ff:ff:ff:ff', dst_ip=ip_virtuale))
        pkt.serialize()
        
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=pkt.data)
        datapath.send_msg(out)
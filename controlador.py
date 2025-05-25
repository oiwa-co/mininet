# Importar las bibliotecas necesarias de os-ken
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from os_ken.controller.handler import set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet
from os_ken.lib.packet import ethernet
from os_ken.lib.packet import ether_types
from os_ken.lib.packet import icmp
from os_ken.lib.packet import ipv4

class SimpleController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleController, self).__init__(*args, **kwargs)
        # Tabla MAC: dpid -> {mac_origen -> puerto_salida}
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Manejador para cuando un switch se conecta. Instala la regla de flujo por defecto.
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Instalar flujo de "table-miss": paquetes sin match van al controlador
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions) # Prioridad 0 (la más baja)

        # --- REGLA DE SEGURIDAD SIMPLE ---
        # Bloquear ICMP de h1 (10.0.0.1) a h3 (10.0.0.3)
        self.logger.info("Instalando regla de bloqueo ICMP para h1 -> h3")
        match_icmp_block = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,  # Es tráfico IP
            ip_proto=1,                       # Es ICMP (protocolo 1)
            ipv4_src='10.0.0.1',                # Origen h1
            ipv4_dst='10.0.0.3'                 # Destino h3
        )
        actions_block = [] # Sin acciones = DROP
        self.add_flow(datapath, 10, match_icmp_block, actions_block) # Prioridad alta (10)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """
        Función auxiliar para añadir reglas de flujo.
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
            datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """
        Manejador para paquetes que llegan al controlador (PacketIn).
        Implementa la lógica del switch L2.
        """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Ignorar paquetes LLDP (Link Layer Discovery Protocol)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})

        # Aprender la MAC de origen para evitar floods futuros
        self.mac_to_port[dpid][src] = in_port
        self.logger.info("Packet IN: dpid=%s src=%s dst=%s in_port=%s", dpid, src, dst, in_port)

        # Decidir el puerto de salida
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD # Si no conocemos el destino, hacer flood

        actions = [parser.OFPActionOutput(out_port)]

        # Instalar un flujo para que no tengamos que procesar este mismo tráfico de nuevo
        if out_port != ofproto.OFPP_FLOOD:
            # --- Aquí podríamos añadir QoS ---
            # Si quisiéramos añadir QoS, podríamos crear un match más específico
            # (e.g., L3/L4) y en las acciones usar `set_queue` si las colas
            # están configuradas en OVS. Por simplicidad, aquí solo hacemos L2.

            # Comprobar si el paquete es IP para hacer match L3/L4 si fuera necesario
            # Aquí solo hacemos match L2 para el switch simple
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)

            # Verificar si el flujo ya existe podría ser una optimización,
            # pero por simplicidad, lo añadimos.
            # Damos una prioridad media (1) para que sea mayor que la de table-miss
            # pero menor que nuestra regla de seguridad.
            self.add_flow(datapath, 1, match, actions, msg.buffer_id)
            self.logger.info("  -> Instalando flujo L2: %s -> %s via puerto %s", src, dst, out_port)
            # Si el buffer_id es válido, enviamos el paquete al instalar el flujo
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                return

        # Si no instalamos un flujo o no usamos el buffer_id, enviamos el paquete manualmente
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

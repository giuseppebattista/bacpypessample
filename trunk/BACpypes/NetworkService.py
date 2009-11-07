
import logging

from copy import copy as _copy

from Debugging import DebugContents
from Exceptions import *

from CommunicationsCore import Client, Server, Bind, \
    ServiceAccessPoint, ApplicationServiceElement

from NPDU import *
from APDU import APDU as _APDU

# some debuging
_log = logging.getLogger(__name__)

# router status values
ROUTER_AVAILABLE = 0            # normal
ROUTER_BUSY = 1                 # router is busy
ROUTER_DISCONNECTED = 2         # could make a connection, but hasn't
ROUTER_UNREACHABLE = 3          # cannot route

#
#   NetworkReference
#

class NetworkReference:
    """These objects map a network to a router."""

    def __init__(self, net, router, status):
        self.network = net
        self.router = router
        self.status = status

#
#   RouterReference
#

class RouterReference(DebugContents):
    """These objects map a router; the adapter to talk to it,
    its address, and a list of networks that it routes to."""

    _debugContents = ('adapter-', 'address', 'networks', 'status')
    
    def __init__(self, adapter, addr, nets, status):
        self.adapter = adapter
        self.address = addr     # local station relative to the adapter
        self.networks = nets    # list of remote networks
        self.status = status    # status as presented by the router

#
#   NetworkAdapter
#

class NetworkAdapter(Client, DebugContents, Logging):

    _debugContents = ('adapterSAP-', 'adapterNet', 'adapterStatus')
    
    def __init__(self, sap, net, status, cid=None):
        Client.__init__(self, cid)
        self.adapterSAP = sap
        self.adapterNet = net
        self.adapterStatus = status

    def Confirmation(self, pdu):
        """Decode upstream PDUs and pass them up to the service access point."""
        NetworkAdapter._debug("Confirmation %r", pdu)

        npdu = NPDU()
        npdu.Decode(pdu)
        self.adapterSAP.ProcessNPDU(self, npdu)

    def ProcessNPDU(self, npdu):
        """Encode NPDUs from the service access point and send them downstream."""
        NetworkAdapter._debug("ProcessNPDU %r", npdu)

        pdu = PDU()
        npdu.Encode(pdu)
        self.Request(pdu)

    def EstablishConnectionToNetwork(self, net):
        pass
        
    def DisconnectConnectionToNetwork(self, net):
        pass
        
#
#   NetworkServiceAccessPoint
#

class NetworkServiceAccessPoint(ServiceAccessPoint, Server, DebugContents, Logging):

    _debugContents = ('adapters++', 'routers++', 'networks+'
        , 'localAdapter-', 'localAddress'
        )
    
    def __init__(self, sap=None, sid=None):
        NetworkServiceAccessPoint._debug("__init__ sap=%r sid=%r", sap, sid)
        ServiceAccessPoint.__init__(self, sap)
        Server.__init__(self, sid)

        self.adapters = []          # list of adapters
        self.routers = {}           # (adapter, address) -> RouterReference
        self.networks = {}          # network -> RouterReference
        
        self.localAdapter = None    # which one is local
        self.localAddress = None    # what is the local address

    def Bind(self, server, net=None, address=None, status=0):
        """Create a network adapter object and bind."""
        NetworkServiceAccessPoint._debug("Bind %r net=%r address=%r status=%r", server, net, address, status)
            
        if (net is None) and self.adapters:
            raise RuntimeError, "already bound"
            
        # create an adapter object
        adapter = NetworkAdapter(self, net, status)
        self.adapters.append(adapter)
        
        # if the address was given, make it the "local" one
        if address:
            self.localAdapter = adapter
            self.localAddress = address
        
        # bind to the server
        Bind(adapter, server)
        
    def Indication(self, pdu):
        NetworkServiceAccessPoint._debug("Indication %r", pdu)
        
        # make sure our configuration is OK
        if (not self.adapters):
            raise ConfigurationError, "no adapters"
            
        if (len(self.adapters) > 1) and (not self.localAdapter):
            raise ConfigurationError, "local adapter must be set"
            
        # get the local adapter
        adapter = self.localAdapter or self.adapters[0]
        
        # build a generic APDU
        apdu = _APDU()
        pdu.Encode(apdu)
        NetworkServiceAccessPoint._debug("    - apdu: %r", apdu)
        
        # build an NPDU specific to where it is going
        npdu = NPDU()
        apdu.Encode(npdu)
        NetworkServiceAccessPoint._debug("    - npdu: %r", npdu)
        
        # the hop count always starts out big
        npdu.npduHopCount = 255
        
        # local broadcast or local stations
        if (npdu.pduDestination.addrType == Address.localBroadcastAddr) or (npdu.pduDestination.addrType == Address.localStationAddr):
            # give it to the adapter
            adapter.ProcessNPDU(npdu)
            return
            
        # global broadcast
        if (npdu.pduDestination.addrType == Address.globalBroadcastAddr):
            # set the destination
            npdu.pduDestination = LocalBroadcast()
            npdu.npduDADR = apdu.pduDestination
            
            # send it to all of the connected adapters
            for xadapter in self.adapters:
                ### make sure the adapter is OK
                xadapter.ProcessNPDU(npdu)
            return
            
        # remote broadcast
        if (npdu.pduDestination.addrType != Address.remoteBroadcastAddr) and (npdu.pduDestination.addrType != Address.remoteStationAddr):
            # can't match the address type
            raise RuntimeError, "invalid destination address type: %s" % (npdu.pduDestination.addrType,)
            
        dnet = npdu.pduDestination.addrNet
        
        # if the network matches the local adapter it's local
        if (dnet == adapter.adapterNet):
            ### log this, the application shouldn't be sending to a remote station address 
            ### when it's a directly connected network
            raise RuntimeError, "addressing problem"
                
        # check for an available path
        if self.networks.has_key(dnet):
            rref = self.networks[dnet]
            adapter = rref.adapter
            
            ### make sure the direct connect is OK, may need to connect
            
            ### make sure the peer router is OK, may need to connect
            
            # fix the destination
            npdu.pduDestination = rref.address
            npdu.npduDADR = apdu.pduDestination
            
            # send it along
            adapter.ProcessNPDU(npdu)
            return
            
        NetworkServiceAccessPoint._debug("    - no known path to network, broadcast to discover it")
            
        # set the destination
        npdu.pduDestination = LocalBroadcast()
        npdu.npduDADR = apdu.pduDestination
        
        # send it to all of the connected adapters
        for xadapter in self.adapters:
            ### make sure the adapter is OK
            xadapter.ProcessNPDU(npdu)
            
    def ProcessNPDU(self, adapter, npdu):
        NetworkServiceAccessPoint._debug("ProcessNPDU %r %r", adapter, npdu)
            
        # make sure our configuration is OK
        if (not self.adapters):
            raise ConfigurationError, "no adapters"
        if (len(self.adapters) > 1) and (not self.localAdapter):
            raise ConfigurationError, "local adapter must be set"
            
        # check for source routing
        if npdu.npduSADR and (npdu.npduSADR.addrType != Address.nullAddr):
            # see if this is attempting to spoof a directly connected network
            snet = npdu.npduSADR.addrNet
            for xadapter in self.adapters:
                if (xadapter is not adapter) and (snet == xadapter.adapterNet):
                    NetworkServiceAccessPoint._warning("spoof?")
                    ### log this
                    return
                    
            # make a key for the router reference
            rkey = (adapter, npdu.pduSource)
            
            # see if this is spoofing an existing routing table entry
            if snet in self.networks:
                rref = self.networks[snet]
                if rref.adapter == adapter and rref.address == npdu.pduSource:
                    pass        # matches current entry
                else:
                    NetworkServiceAccessPoint._debug("    - replaces entry")
                    
                    ### check to see if this source could be a router to the new network
                    
                    # remove the network from the rref
                    i = rref.networks.index(snet)
                    del rref.networks[i]
                    
                    # remove the network
                    del self.networks[snet]
                    
            # get the router reference for this router
            rref = self.routers.get(rkey)
            if rref:
                if snet not in rref.networks:
                    # add the network
                    rref.networks.append(snet)
                    
                    # reference the snet
                    self.networks[snet] = rref
            else:
                # new reference
                rref = RouterReference( adapter, npdu.pduSource, [snet], 0)
                self.routers[rkey] = rref
                
                # reference the snet
                self.networks[snet] = rref
                
        # check for destination routing
        if (not npdu.npduDADR) or (npdu.npduDADR.addrType == Address.nullAddr):
            processLocally = (not self.localAdapter) or (adapter is self.localAdapter)
            forwardMessage = False
            
        elif npdu.npduDADR.addrType == Address.remoteBroadcastAddr:
            if not self.localAdapter:
                return
            if (npdu.npduDADR.addrNet == adapter.adapterNet):
                ### log this, attempt to route to a network the device is already on
                return
                
            processLocally = (npdu.npduDADR.addrNet == self.localAdapter.adapterNet)
            forwardMessage = True
        
        elif npdu.npduDADR.addrType == Address.remoteStationAddr:
            if not self.localAdapter:
                return
            if (npdu.npduDADR.addrNet == adapter.adapterNet):
                ### log this, attempt to route to a network the device is already on
                return
                
            processLocally = (npdu.npduDADR.addrNet == self.localAdapter.adapterNet) \
                and (npdu.npduDADR.addrAddr == self.localAddress.addrAddr)
            forwardMessage = not processLocally
        
        elif npdu.npduDADR.addrType == Address.globalBroadcastAddr:
            processLocally = True
            forwardMessage = True
        
        else:
            ### invalid destination address type
            return
            
        NetworkServiceAccessPoint._debug("    - processLocally: %r", processLocally)
        NetworkServiceAccessPoint._debug("    - forwardMessage: %r", forwardMessage)
        
        # application or network layer message
        if npdu.npduNetMessage is None:
            if processLocally and self.serverPeer:
                # decode as a generic APDU
                apdu = _APDU()
                apdu.Decode(_copy(npdu))
                NetworkServiceAccessPoint._debug("    - apdu: %r", apdu)
                
                # see if it needs to look routed
                if (len(self.adapters) > 1) and (adapter != self.localAdapter):
                    # combine the source address
                    if not npdu.npduSADR:
                        apdu.pduSource = RemoteStation( adapter.adapterNet, npdu.pduSource.addrAddr )
                    else:
                        apdu.pduSource = npdu.npduSADR
                        
                    # map the destination
                    if not npdu.npduDADR:
                        apdu.pduDestination = self.localAddress
                    elif npdu.npduDADR.addrType == Address.globalBroadcastAddr:
                        apdu.pduDestination = npdu.npduDADR
                    elif npdu.npduDADR.addrType == Address.remoteBroadcastAddr:
                        apdu.pduDestination = LocalBroadcast()
                    else:
                        apdu.pduDestination = self.localAddress
                else:
                    # combine the source address
                    if npdu.npduSADR:
                        apdu.pduSource = npdu.npduSADR
                    else:
                        apdu.pduSource = npdu.pduSource
                                                
                    # pass along global broadcast
                    if npdu.npduDADR and npdu.npduDADR.addrType == Address.globalBroadcastAddr:
                        apdu.pduDestination = npdu.npduDADR
                    else:
                        apdu.pduDestination = npdu.pduDestination
                
                # pass upstream to the application layer
                self.Response(apdu)
                
            if not forwardMessage:
                return
        else:
            if processLocally:
                # do a deeper decode of the NPDU
                xpdu = NPDUTypes[npdu.npduNetMessage]()
                xpdu.Decode(_copy(npdu))
                
                # pass to the service element
                self.SAPRequest(adapter, xpdu)
                
            if not forwardMessage:
                return
        
        # make sure we're really a router
        if (len(self.adapters) == 1):
            return
        
        # make sure it hasn't looped 
        if (npdu.npduHopCount == 0):
            return
            
        # build a new NPDU to send to other adapters
        newpdu = _copy(npdu)
        
        # clear out the source and destination
        newpdu.pduSource = None
        newpdu.pduDestination = None
        
        # decrease the hop count
        newpdu.npduHopCount -= 1
        
        # set the source address
        if not npdu.npduSADR:
            newpdu.npduSADR = RemoteStation( adapter.adapterNet, npdu.pduSource.addrAddr )
        else:
            newpdu.npduSADR = npdu.npduSADR
        
        # if this is a broadcast it goes everywhere
        if npdu.npduDADR.addrType == Address.globalBroadcastAddr:
            newpdu.pduDestination = LocalBroadcast()
            
            for xadapter in self.adapters:
                if (xadapter is not adapter):
                    xadapter.ProcessNPDU(newpdu)
            return
            
        if (npdu.npduDADR.addrType == Address.remoteBroadcastAddr) \
                or (npdu.npduDADR.addrType == Address.remoteStationAddr):
            dnet = npdu.npduDADR.addrNet
            
            # see if this should go to one of our directly connected adapters
            for xadapter in self.adapters:
                if dnet == xadapter.adapterNet:
                    NetworkServiceAccessPoint._debug("    - found direct connect via %r", xadapter)
                    if (npdu.npduDADR.addrType == Address.remoteBroadcastAddr):
                        newpdu.pduDestination = LocalBroadcast()
                    else:
                        newpdu.pduDestination = LocalStation(npdu.npduDADR.addrAddr)
                        
                    # last leg in routing
                    newpdu.npduDADR = None
                    
                    # send the packet downstream
                    xadapter.ProcessNPDU(newpdu)
                    return
            
            # see if we know how to get there
            if dnet in self.networks:
                rref = self.networks[dnet]
                newpdu.pduDestination = rref.address
                
                ### check to make sure the router is OK
                
                ### check to make sure the network is OK, may need to connect
                
                NetworkServiceAccessPoint._debug("    - newpdu: %r", newpdu)
                    
                # send the packet downstream
                rref.adapter.ProcessNPDU(newpdu)
                return
                
            ### queue this message for reprocessing when the response comes back
            
            # try to find a path to the network
            xnpdu = WhoIsRouterToNetwork(dnet)
            xnpdu.pduDestination = LocalBroadcast()
            
            # send it to all of the connected adapters
            for xadapter in self.adapters:
                # skip the horse it rode in on
                if (xadapter is adapter):
                    continue
                    
                ### make sure the adapter is OK
                self.SAPIndication(xadapter, xnpdu)
            
        ### log this, what to do?
        return
        
    def SAPIndication(self, adapter, npdu):
        NetworkServiceAccessPoint._debug("SAPIndication %r %r", adapter, npdu)
            
        # encode it as a generic NPDU
        xnpdu = NPDU()
        npdu.Encode(xnpdu)
        
        # tell the adapter to process the NPDU
        adapter.ProcessNPDU(xnpdu)

    def SAPConfirmation(self, adapter, npdu):
        NetworkServiceAccessPoint._debug("SAPConfirmation %r %r", adapter, npdu)
            
        # encode it as a generic NPDU
        xnpdu = NPDU()
        npdu.Encode(xnpdu)
        
        # tell the adapter to process the NPDU
        adapter.ProcessNPDU(xnpdu)

#
#   NetworkServiceElement
#

class NetworkServiceElement(ApplicationServiceElement):

    def __init__(self, eid=None):
        NetworkServiceElement._debug("__init__ eid=%r", eid)
        ApplicationServiceElement.__init__(self, eid)
        
    def Indication(self, adapter, npdu):
        NetworkServiceElement._debug("Indication %r %r", adapter, npdu)
        
        # redirect
        fn = npdu.__class__.__name__
        if hasattr(self, fn):
            getattr(self, fn)(adapter, npdu)
    
    def Confirmation(self, adapter, npdu):
        NetworkServiceElement._debug("Confirmation %r %r", adapter, npdu)
            
        # redirect
        fn = npdu.__class__.__name__
        if hasattr(self, fn):
            getattr(self, fn)(adapter, npdu)
        
    #-----
    
    def WhoIsRouterToNetwork(self, adapter, npdu):
        NetworkServiceElement._debug("WhoIsRouterToNetwork %r %r", adapter, npdu)
            
        # reference the service access point
        sap = self.elementService
        
        # if we're not a router, skip it
        if len(sap.adapters) == 1:
            return
            
        if npdu.wirtnNetwork is None:
            # requesting all networks
            netlist = []
            
            # start with directly connected networks
            for xadapter in sap.adapters:
                if (xadapter is not adapter):
                    netlist.append(xadapter.adapterNet)
                    
            # build a list of other available networks
            for net, rref in sap.networks.items():
                if rref.adapter is not adapter:
                    ### skip those marked unreachable
                    ### skip those that are not available
                    netlist.append(net)
                    
            if netlist:
                # build a response
                iamrtn = IAmRouterToNetwork(netlist)
                iamrtn.pduDestination = LocalBroadcast()
                
                # send it back
                self.Response(adapter, iamrtn)
                
        else:
            # requesting a specific network
            if npdu.wirtnNetwork in sap.networks:
                rref = sap.networks[npdu.wirtnNetwork]
                if rref.adapter is adapter:
                    pass    # this router on the same network as the request
                else:
                    # build a response
                    iamrtn = IAmRouterToNetwork([npdu.wirtnNetwork])
                    iamrtn.pduDestination = LocalBroadcast()
                    
                    # send it back
                    self.Response(adapter, iamrtn)
                    
            else:
                # build a request
                whoisrtn = WhoIsRouterToNetwork(npdu.wirtnNetwork)
                whoisrtn.pduDestination = LocalBroadcast()
                
                # if the request had a source, forward it along
                if npdu.npduSADR:
                    whoisrtn.npduSADR = npdu.npduSADR
                else:
                    whoisrtn.npduSADR = RemoteStation(adapter.adapterNet, npdu.pduSource.addrAddr)
                
                # send it to all of the (other) adapters
                for xadapter in sap.adapters:
                    if xadapter is not adapter:
                        self.Request(xadapter, npdu)
                        
    def IAmRouterToNetwork(self, adapter, npdu):
        NetworkServiceElement._debug("IAmRouterToNetwork %r %r", adapter, npdu)
            
        # reference the service access point
        sap = self.elementService
        
        # make a key for the router reference
        rkey = (adapter, npdu.pduSource)
        
        for snet in npdu.iartnNetworkList:
            # see if this is spoofing an existing routing table entry
            if snet in sap.networks:
                rref = sap.networks[snet]
                    
                if rref.adapter == adapter and rref.address == npdu.pduSource:
                    pass        # matches current entry"
                else:
                    ### check to see if this source could be a router to the new network
                    
                    # remove the network from the rref
                    i = rref.networks.index(snet)
                    del rref.networks[i]
                    
                    # remove the network
                    del sap.networks[snet]
                    
            ### check to see if it is OK to add the new entry
            
            # get the router reference for this router
            rref = sap.routers.get(rkey)
            if rref:
                if snet not in rref.networks:
                    # add the network
                    rref.networks.append(snet)
                    
                    # reference the snet
                    sap.networks[snet] = rref
            else:
                # new reference
                rref = RouterReference( adapter, npdu.pduSource, [snet], 0)
                sap.routers[rkey] = rref
                
                # reference the snet
                sap.networks[snet] = rref
                
    def ICouldBeRouterToNetwork(self, adapter, npdu):
        NetworkServiceElement._debug("ICouldBeRouterToNetwork %r %r", adapter, npdu)
        
        # reference the service access point
        sap = self.elementService
        
    def RejectMessageToNetwork(self, adapter, npdu):
        NetworkServiceElement._debug("RejectMessageToNetwork %r %r", adapter, npdu)
        
        # reference the service access point
        sap = self.elementService
        
    def RouterBusyToNetwork(self, adapter, npdu):
        NetworkServiceElement._debug("RouterBusyToNetwork %r %r", adapter, npdu)
        
        # reference the service access point
        sap = self.elementService
        
    def RouterAvailableToNetwork(self, adapter, npdu):
        NetworkServiceElement._debug("RouterAvailableToNetwork %r %r", adapter, npdu)
        
        # reference the service access point
        sap = self.elementService
        
    def InitializeRoutingTable(self, adapter, npdu):
        NetworkServiceElement._debug("InitializeRoutingTable %r %r", adapter, npdu)
        
        # reference the service access point
        sap = self.elementService
        
    def InitializeRoutingTableAck(self, adapter, npdu):
        NetworkServiceElement._debug("InitializeRoutingTableAck %r %r", adapter, npdu)
        
        # reference the service access point
        sap = self.elementService
        
    def EstablishConnectionToNetwork(self, adapter, npdu):
        NetworkServiceElement._debug("EstablishConnectionToNetwork %r %r", adapter, npdu)
        
        # reference the service access point
        sap = self.elementService
        
    def DisconnectConnectionToNetwork(self, adapter, npdu):
        NetworkServiceElement._debug("DisconnectConnectionToNetwork %r %r", adapter, npdu)
        
        # reference the service access point
        sap = self.elementService


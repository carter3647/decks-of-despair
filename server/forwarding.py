import upnpclient
import socket
from shared.useful import warn,error,sprint

igd_service = None

def get_lan_ip() -> str:
    """
    Creates a dummy UDP connection to force the OS to choose 
    the active network interface routing traffic to the internet.
    """
    # Create a UDP socket (SOCK_DGRAM) using IPv4 (AF_INET)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 8.8.8.8 is Google DNS. The port (80) does not matter.
        # No actual packets are transmitted during this connect() call for UDP.
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
    except Exception:
        # Fallback to localhost if the machine has no network interfaces active
        warn("No network interfaces! Defaulting to localhost.")
        lan_ip = "127.0.0.1"
    finally:
        s.close()
    
    return lan_ip

def add_port_forward(external_port,internal_port):
    sprint("Searching for UPnP devices...")
    devices = upnpclient.discover()
    
    # 2. Find a device that supports WANIPConnection or WANPPPConnection (the router)
    router = None
    global igd_service
    for device in devices:
        # Search through services for an Internet Gateway Device (IGD) profile
        for service in device.services:
            if "WANIPConnection" in service.service_type or "WANPPPConnection" in service.service_type:
                router = device
                igd_service = service
                break
        if router:
            break

    if not router or not igd_service:
        error("No UPnP-enabled router or IGD service found.")
        return

    sprint(f"Connected to router: {router.friendly_name}")

    # Define configuration details
    internal_client = get_lan_ip()
    description = "Steam Remote Play Test"

    # 3. Add a port mapping
    try:
        sprint(f"Attempting to map external port {external_port} to {internal_client}:{internal_port}...")
        igd_service.AddPortMapping(
            NewRemoteHost="",                  # Clear/blank means allow any external host
            NewExternalPort=external_port,
            NewProtocol="TCP",
            NewInternalPort=internal_port,
            NewInternalClient=internal_client,
            NewEnabled=True,
            NewPortMappingDescription=description,
            NewLeaseDuration=0                 # 0 means permanent until deleted
        )
        sprint("Port mapping added successfully!")
        
    except Exception as e:
        error(f"Failed to add port mapping: {e}")
        return

def del_port_forward(external_port):
    try:
        igd_service.DeletePortMapping(
            NewRemoteHost="",
            NewExternalPort=external_port,
            NewProtocol="TCP"
        )
        sprint("Port mapping removed successfully.")
    except Exception as e:
        error(f"Failed to remove port mapping: {e}\nWas this mapping initialized?")

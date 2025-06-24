"""Network site mapping and device tracking functionality."""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

from .database import get_database_adapter, calculate_data_hash, DatabaseAdapter


@dataclass
class NetworkDevice:
    """Represents a discovered network device."""
    hostname: str
    connection_ip: str
    last_seen: str
    status: str  # success, error
    cpu_model: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_total: Optional[str] = None
    memory_used: Optional[str] = None
    memory_free: Optional[str] = None
    memory_available: Optional[str] = None
    disk_filesystem: Optional[str] = None
    disk_size: Optional[str] = None
    disk_used: Optional[str] = None
    disk_available: Optional[str] = None
    disk_use_percent: Optional[str] = None
    disk_mount: Optional[str] = None
    network_interfaces: Optional[str] = None  # JSON string
    uptime: Optional[str] = None
    os_info: Optional[str] = None
    error_message: Optional[str] = None


class NetworkSiteMap:
    """Manages the network site map database."""
    
    def __init__(self, db_path: Optional[str] = None, db_type: Optional[str] = None, **db_kwargs):
        """Initialize the site map with database connection."""
        self.db_adapter = get_database_adapter(
            db_type=db_type,
            db_path=db_path,
            **db_kwargs
        )
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the database schema."""
        self.db_adapter.init_schema()
    
    def parse_discovery_output(self, discovery_json: str) -> NetworkDevice:
        """Parse SSH discovery output into a NetworkDevice object."""
        try:
            data = json.loads(discovery_json)
            
            device = NetworkDevice(
                hostname=data.get('hostname', ''),
                connection_ip=data.get('connection_ip', ''),
                last_seen=datetime.now().isoformat(),
                status=data.get('status', 'error')
            )
            
            if data.get('status') == 'success' and 'data' in data:
                discovery_data = data['data']
                
                # CPU information
                if 'cpu' in discovery_data:
                    cpu_info = discovery_data['cpu']
                    device.cpu_model = cpu_info.get('model')
                    try:
                        device.cpu_cores = int(cpu_info.get('cores', 0))
                    except (ValueError, TypeError):
                        device.cpu_cores = None
                
                # Memory information
                if 'memory' in discovery_data:
                    mem_info = discovery_data['memory']
                    device.memory_total = mem_info.get('total')
                    device.memory_used = mem_info.get('used')
                    device.memory_free = mem_info.get('free')
                    device.memory_available = mem_info.get('available')
                
                # Disk information
                if 'disk' in discovery_data:
                    disk_info = discovery_data['disk']
                    device.disk_filesystem = disk_info.get('filesystem')
                    device.disk_size = disk_info.get('size')
                    device.disk_used = disk_info.get('used')
                    device.disk_available = disk_info.get('available')
                    device.disk_use_percent = disk_info.get('use_percent')
                    device.disk_mount = disk_info.get('mount')
                
                # Network interfaces (store as JSON)
                if 'network' in discovery_data:
                    device.network_interfaces = json.dumps(discovery_data['network'])
                
                # System information
                device.uptime = discovery_data.get('uptime')
                device.os_info = discovery_data.get('os')
            
            elif data.get('status') == 'error':
                device.error_message = data.get('error', 'Unknown error')
            
            return device
            
        except json.JSONDecodeError as e:
            # Create error device for invalid JSON
            return NetworkDevice(
                hostname='unknown',
                connection_ip='unknown',
                last_seen=datetime.now().isoformat(),
                status='error',
                error_message=f'JSON parse error: {str(e)}'
            )
    
    def store_device(self, device: NetworkDevice) -> int:
        """Store or update a device in the database."""
        device_data = asdict(device)
        return self.db_adapter.store_device(device_data)
    
    def store_discovery_history(self, device_id: int, discovery_data: str) -> None:
        """Store discovery data in history for change tracking."""
        data_hash = calculate_data_hash(discovery_data)
        self.db_adapter.store_discovery_history(device_id, discovery_data, data_hash)
    
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all devices from the database."""
        return self.db_adapter.get_all_devices()
    
    def get_device_changes(self, device_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get change history for a specific device."""
        return self.db_adapter.get_device_changes(device_id, limit)
    
    def analyze_network_topology(self) -> Dict[str, Any]:
        """Analyze the network topology and provide insights."""
        devices = self.get_all_devices()
        
        analysis = {
            'total_devices': len(devices),
            'online_devices': len([d for d in devices if d['status'] == 'success']),
            'offline_devices': len([d for d in devices if d['status'] == 'error']),
            'operating_systems': {},
            'cpu_architectures': {},
            'network_segments': {},
            'resource_utilization': {
                'high_memory_usage': [],
                'high_disk_usage': [],
                'low_resources': []
            }
        }
        
        for device in devices:
            if device['status'] != 'success':
                continue
            
            # OS distribution
            os_info = device.get('os_info', 'Unknown')
            analysis['operating_systems'][os_info] = analysis['operating_systems'].get(os_info, 0) + 1
            
            # CPU models
            cpu_model = device.get('cpu_model', 'Unknown')
            analysis['cpu_architectures'][cpu_model] = analysis['cpu_architectures'].get(cpu_model, 0) + 1
            
            # Network segments (by IP prefix)
            connection_ip = device.get('connection_ip', '')
            if '.' in connection_ip:
                network_prefix = '.'.join(connection_ip.split('.')[:3]) + '.0/24'
                analysis['network_segments'][network_prefix] = analysis['network_segments'].get(network_prefix, 0) + 1
            
            # Resource utilization analysis
            if device.get('disk_use_percent'):
                try:
                    disk_usage = int(device['disk_use_percent'].rstrip('%'))
                    if disk_usage > 80:
                        analysis['resource_utilization']['high_disk_usage'].append({
                            'hostname': device['hostname'],
                            'usage': device['disk_use_percent']
                        })
                except (ValueError, AttributeError):
                    pass
            
            # Identify resource-constrained devices
            if device.get('cpu_cores') and device.get('cpu_cores') <= 2:
                if device.get('memory_total') and 'G' in str(device['memory_total']):
                    try:
                        memory_gb = float(device['memory_total'].rstrip('G'))
                        if memory_gb <= 2:
                            analysis['resource_utilization']['low_resources'].append({
                                'hostname': device['hostname'],
                                'cpu_cores': device['cpu_cores'],
                                'memory': device['memory_total']
                            })
                    except (ValueError, AttributeError):
                        pass
        
        return analysis
    
    def suggest_deployments(self) -> Dict[str, Any]:
        """Suggest optimal deployment locations based on current network state."""
        devices = self.get_all_devices()
        online_devices = [d for d in devices if d['status'] == 'success']
        
        suggestions = {
            'load_balancer_candidates': [],
            'database_candidates': [],
            'monitoring_targets': [],
            'upgrade_recommendations': []
        }
        
        for device in online_devices:
            hostname = device['hostname']
            
            # Load balancer candidates (high CPU, good memory)
            cpu_cores = device.get('cpu_cores') or 0
            if cpu_cores >= 4:
                memory_gb = 0
                if device.get('memory_total') and 'G' in str(device['memory_total']):
                    try:
                        memory_gb = float(device['memory_total'].rstrip('G'))
                    except (ValueError, AttributeError):
                        pass
                
                if memory_gb >= 4:
                    suggestions['load_balancer_candidates'].append({
                        'hostname': hostname,
                        'reason': f"{cpu_cores} cores, {device['memory_total']} RAM"
                    })
            
            # Database candidates (good disk space, memory)
            if device.get('disk_use_percent'):
                try:
                    disk_usage = int(device['disk_use_percent'].rstrip('%'))
                    if disk_usage < 50:  # Plenty of disk space
                        memory_gb = 0
                        if device.get('memory_total') and 'G' in str(device['memory_total']):
                            try:
                                memory_gb = float(device['memory_total'].rstrip('G'))
                            except (ValueError, AttributeError):
                                pass
                        
                        if memory_gb >= 8:
                            suggestions['database_candidates'].append({
                                'hostname': hostname,
                                'reason': f"Low disk usage ({device['disk_use_percent']}), {device['memory_total']} RAM"
                            })
                except (ValueError, AttributeError):
                    pass
            
            # Monitoring targets (all online devices should be monitored)
            suggestions['monitoring_targets'].append({
                'hostname': hostname,
                'connection_ip': device['connection_ip'],
                'os': device.get('os_info', 'Unknown')
            })
            
            # Upgrade recommendations
            cpu_cores = device.get('cpu_cores') or 0
            if cpu_cores <= 2:
                memory_gb = 0
                if device.get('memory_total') and 'G' in str(device['memory_total']):
                    try:
                        memory_gb = float(device['memory_total'].rstrip('G'))
                    except (ValueError, AttributeError):
                        pass
                
                if memory_gb <= 4:
                    suggestions['upgrade_recommendations'].append({
                        'hostname': hostname,
                        'reason': f"Limited resources: {cpu_cores} cores, {device.get('memory_total', 'Unknown')} RAM"
                    })
        
        return suggestions


async def discover_and_store(
    sitemap: NetworkSiteMap,
    hostname: str,
    username: str,
    password: Optional[str] = None,
    key_path: Optional[str] = None,
    port: int = 22
) -> str:
    """Discover a device and store it in the site map."""
    from .ssh_tools import ssh_discover_system
    
    # Perform discovery
    discovery_result = await ssh_discover_system(hostname, username, password, key_path, port)
    
    # Parse and store the result
    device = sitemap.parse_discovery_output(discovery_result)
    device_id = sitemap.store_device(device)
    sitemap.store_discovery_history(device_id, discovery_result)
    
    return json.dumps({
        'status': 'success',
        'device_id': device_id,
        'hostname': device.hostname,
        'discovery_status': device.status,
        'stored_at': datetime.now().isoformat()
    }, indent=2)


async def bulk_discover_and_store(
    sitemap: NetworkSiteMap,
    targets: List[Dict[str, Any]]
) -> str:
    """Discover multiple devices and store them in the site map."""
    results = []
    
    for target in targets:
        try:
            result = await discover_and_store(
                sitemap,
                target['hostname'],
                target['username'],
                target.get('password'),
                target.get('key_path'),
                target.get('port', 22)
            )
            results.append(json.loads(result))
        except Exception as e:
            results.append({
                'status': 'error',
                'hostname': target.get('hostname', 'unknown'),
                'error': str(e)
            })
    
    return json.dumps({
        'status': 'success',
        'total_targets': len(targets),
        'results': results,
        'completed_at': datetime.now().isoformat()
    }, indent=2)
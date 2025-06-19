"""
Certificate finder utility for MQTT CLI.
"""
import os
import csv
from datetime import datetime
import click
from pathlib import Path
from typing import Optional, Tuple, List
import logging
from .debug_logger import debug_log, debug_step

# Get logger for this module
logger = logging.getLogger(__name__)

@debug_step("Converting Unix path to Windows")
def convert_unix_path_to_windows(unix_path: str, base_path: str) -> str:
    """Convert Unix-style path to Windows path relative to base_path."""
    try:
        # Extract the relative path after esp-rainmaker-admin-cli
        if 'esp-rainmaker-admin-cli' in unix_path:
            relative_path = unix_path.split('esp-rainmaker-admin-cli/')[-1]
            # Convert to Windows path and join with base_path
            logger.debug(f"Converting path {unix_path} to Windows format")
            result = str(Path(base_path) / relative_path)
            logger.debug(f"Converted path: {result}")
            return result
        return unix_path
    except Exception as e:
        logger.debug(f"Path conversion failed: {str(e)}")
        return unix_path

@debug_step("Reading node info file")
def read_node_info_file(file_path: Path) -> Optional[str]:
    """
    Read node.info file and extract node_id.
    
    Args:
        file_path: Path to node.info file
        
    Returns:
        str: node_id if found, None otherwise
    """
    try:
        logger.debug(f"Reading node.info file: {file_path}")
        with open(file_path, 'r') as f:
            content = f.read().strip()
            logger.debug(f"Found node_id: {content}")
            return content
    except Exception as e:
        logger.debug(f"Failed to read node.info file: {str(e)}")
        return None

@debug_step("Finding certificates by MAC address")
def find_by_mac_address(base_path: str, mac_address: str, node_id: str) -> Optional[Tuple[str, str]]:
    """
    Find certificate and key files by MAC address directory.
    
    Args:
        base_path: Base directory to search
        mac_address: 12-digit alphanumeric MAC address
        node_id: Node ID to validate against node.info
        
    Returns:
        tuple: (cert_path, key_path) if found, None otherwise
    """
    base_path = Path(base_path)
    mac_dir = base_path / mac_address
    
    logger.debug(f"Looking for certificates in MAC directory: {mac_dir}")
    
    # Check if MAC directory exists
    if mac_dir.exists() and mac_dir.is_dir():
        logger.debug("Found MAC address directory")
        # Check node.info file
        node_info_path = mac_dir / 'node.info'
        if node_info_path.exists():
            stored_node_id = read_node_info_file(node_info_path)
            if stored_node_id == node_id:
                logger.debug(f"Node ID match found: {node_id}")
                # Found matching directory, look for cert and key
                cert_path = mac_dir / 'node.crt'
                key_path = mac_dir / 'node.key'
                if cert_path.exists() and key_path.exists():
                    logger.debug(f"Found certificate files: {cert_path}, {key_path}")
                    return str(cert_path), str(key_path)
                else:
                    logger.debug("Certificate files not found in MAC directory")
            else:
                logger.debug(f"Node ID mismatch. Expected: {node_id}, Found: {stored_node_id}")
        else:
            logger.debug("node.info file not found in MAC directory")
    else:
        logger.debug("MAC address directory not found")
    
    return None

@debug_step("Finding node certificate key pairs")
def find_node_cert_key_pairs(base_path: str) -> List[Tuple[str, str, str]]:
    """
    Find all node ID, certificate, and key file pairs.
    Searches in node_details directory structure.
    
    Args:
        base_path: Base directory to search
    
    Returns:
        list: List of tuples containing (node_id, cert_path, key_path)
    """
    node_pairs = []
    base_path = Path(base_path)
    
    logger.debug(f"Searching for certificate pairs in {base_path}")
    
    try:
        # Find all node folders in node_details structure
        node_folders = find_node_folders(base_path)
        logger.debug(f"Found {len(node_folders)} node folders")

        for node_id, folder_path in node_folders:
            try:
                crt_path, key_path = find_crt_key_files(folder_path)
                if crt_path and key_path:
                    logger.debug(f"Found valid certificate pair for node {node_id}")
                    node_pairs.append((node_id, str(crt_path), str(key_path)))
                else:
                    logger.debug(f"Certificate files not found for node {node_id}")
            except Exception as e:
                logger.debug(f"Error processing node folder {folder_path}: {str(e)}")
                click.echo(click.style(f"Error processing node folder {folder_path}: {str(e)}", fg='yellow'))
                
    except Exception as e:
        logger.debug(f"Error accessing directory {base_path}: {str(e)}")
        click.echo(click.style(f"Error accessing directory {base_path}: {str(e)}", fg='yellow'))
    
    logger.debug(f"Found {len(node_pairs)} total certificate pairs")
    return node_pairs

@debug_step("Getting certificate and key paths")
def get_cert_and_key_paths(base_path: str, node_id: str) -> Tuple[str, str]:
    """Find certificate and key paths for a node."""
    logger.debug(f"Searching for certificates for node {node_id} in {base_path}")
    node_pairs = find_node_cert_key_pairs(base_path)
    
    for nodeID, cert_path, key_path in node_pairs:
        if str(nodeID) == str(node_id):
            logger.debug(f"Found certificates for node {node_id}")
            return cert_path, key_path
            
    logger.debug(f"No certificates found for node {node_id}")
    raise FileNotFoundError(f"Certificate and key not found for node {node_id}")

@debug_step("Getting root certificate path")
def get_root_cert_path(config_dir: Path) -> str:
    """Get path to root CA certificate."""
    logger.debug(f"Looking for root certificate in {config_dir}")
    
    # First check in config directory
    root_path = config_dir / 'certs' / 'root.pem'
    if root_path.exists():
        logger.debug(f"Found root certificate in config directory: {root_path}")
        return str(root_path)
        
    # Then check in package directory
    package_root = Path(__file__).resolve().parent.parent.parent
    root_path = package_root / 'certs' / 'root.pem'
    if root_path.exists():
        logger.debug(f"Found root certificate in package directory: {root_path}")
        return str(root_path)
        
    logger.debug("Root certificate not found in any location")
    raise FileNotFoundError("Root CA certificate not found")


# ---------------

def find_node_folders(base_path):
    """
    Search through base_path to find all node_details folders and then node-xxxxxx-node_id folders
    Returns a list of tuples with (node_id, full_path)
    """
    node_folders = []
    base_path = Path(base_path)

    # Walk through the directory structure
    for root, dirs, files in os.walk(base_path):
        # Check if current directory is node_details
        if Path(root).name == "node_details":
            # Look for node-xxxxxx-node_id folders
            for dir_name in dirs:
                if dir_name.startswith("node-") and "-" in dir_name[6:]:
                    # Extract node_id (part after the 6th dash)
                    node_id = dir_name.split("-", 6)[-1]
                    full_path = Path(root) / dir_name
                    node_folders.append((node_id, full_path))

    return node_folders


def find_crt_key_files(folder_path):
    """
    Find certificate and key files in the node folder
    Returns (crt_path, key_path) or (None, None) if not found
    """
    # List of possible certificate file names to check
    crt_candidates = [
        "node.crt",  # Primary candidate
        "crt-node.crt",  # Fallback candidate
        "certificate.crt",  # Additional fallback
    ]

    # List of possible key file names to check
    key_candidates = [
        "node.key",  # Primary candidate
        "key-node.key",  # Fallback candidate
        "private.key",  # Additional fallback
    ]

    # Check for certificate file
    crt_path = None
    for candidate in crt_candidates:
        test_path = folder_path / candidate
        if test_path.exists():
            crt_path = test_path
            break

    # Check for key file
    key_path = None
    for candidate in key_candidates:
        test_path = folder_path / candidate
        if test_path.exists():
            key_path = test_path
            break

    return crt_path, key_path


def find_node_cert_key_pairs_path(base_path):
    """
    Find all node ID, certificate, and key file pairs from node folders.

    Returns:
        list: List of tuples containing (node_id, cert_path, key_path)
    """
    node_pairs = []
    base_path = Path(base_path)

    # Find all node folders
    nodes = find_node_folders(base_path)

    for node_id, folder_path in nodes:
        crt_path, key_path = find_crt_key_files(folder_path)

        if crt_path and key_path:
            # Convert paths to strings
            node_pairs.append((
                node_id,
                str(crt_path.resolve()),
                str(key_path.resolve())
            ))
        else:
            print(f"Warning: Certificate files not found for node {node_id} in {folder_path}")

    return node_pairs

def get_cert_paths_from_direct_path(base_path: str, node_id: str, mac_address: Optional[str] = None) -> Tuple[str, str]:
    """
    Find certificate and key paths for a node when using direct path.
    This is used when --cert-path is provided in CLI.
    
    Args:
        base_path: Base directory to search
        node_id: Node ID to find certificates for
        mac_address: Optional 12-digit alphanumeric MAC address
        
    Returns:
        tuple: (cert_path, key_path)
        
    Raises:
        FileNotFoundError: If certificates are not found
    """
    base_path = Path(base_path)
    
    # If MAC address is provided, try finding by MAC first
    if mac_address:
        result = find_by_mac_address(base_path, mac_address, node_id)
        if result:
            return result
    
    # If MAC search failed or wasn't requested, try the node_details structure
    node_folders = find_node_folders(base_path)
    for folder_node_id, folder_path in node_folders:
        if folder_node_id == node_id:
            crt_path, key_path = find_crt_key_files(folder_path)
            if crt_path and key_path:
                return str(crt_path), str(key_path)
            
    raise FileNotFoundError(f"Certificate files not found for node {node_id} in {base_path}")
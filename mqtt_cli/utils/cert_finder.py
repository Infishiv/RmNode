"""
Certificate finder utility for MQTT CLI.
"""
import os
import csv
from datetime import datetime
import click
from pathlib import Path
from typing import Optional, Tuple, List

def convert_unix_path_to_windows(unix_path: str, base_path: str) -> str:
    """Convert Unix-style path to Windows path relative to base_path."""
    try:
        # Extract the relative path after esp-rainmaker-admin-cli
        if 'esp-rainmaker-admin-cli' in unix_path:
            relative_path = unix_path.split('esp-rainmaker-admin-cli/')[-1]
            # Convert to Windows path and join with base_path
            return str(Path(base_path) / relative_path)
        return unix_path
    except Exception:
        return unix_path

def find_node_cert_key_pairs(base_path: str, is_rainmaker: bool = False) -> List[Tuple[str, str, str]]:
    """
    Find all node ID, certificate, and key file pairs.
    First tries CSV files, then falls back to direct directory search.
    
    Args:
        base_path: Base directory to search
        is_rainmaker: Whether to use Rainmaker-specific search logic
    
    Returns:
        list: List of tuples containing (node_id, cert_path, key_path)
    """
    node_pairs = []
    base_path = Path(base_path)
    
    if is_rainmaker:
        # Rainmaker-specific search logic
        try:
            # Find all yyyy-mm-dd directories
            date_dirs = []
            for entry in os.listdir(base_path):
                full_path = base_path / entry
                if full_path.is_dir():
                    try:
                        datetime.strptime(entry, '%Y-%m-%d')
                        date_dirs.append(full_path)
                    except ValueError:
                        continue

            for date_dir in date_dirs:
                # Find all Mfg-xxxxxx directories
                mfg_dirs = [d for d in os.listdir(date_dir)
                           if (date_dir / d).is_dir() and d.startswith('Mfg-')]

                for mfg_dir in mfg_dirs:
                    mfg_path = date_dir / mfg_dir
                    csv_dir_path = mfg_path / 'csv'
                    
                    if not csv_dir_path.is_dir():
                        continue

                    # Process all CSV files in the directory
                    csv_files = [f for f in os.listdir(csv_dir_path) if f.endswith('.csv')]
                    
                    for csv_file in csv_files:
                        csv_path = csv_dir_path / csv_file
                        node_id = csv_file.replace('.csv', '').split('-', 2)[-1]  # Extract node ID from filename
                        
                        try:
                            with open(csv_path, mode='r') as file:
                                reader = csv.DictReader(file)
                                cert_path = None
                                key_path = None
                                
                                for row in reader:
                                    if row['key'] == 'client_cert':
                                        cert_path = convert_unix_path_to_windows(row['value'], base_path)
                                    elif row['key'] == 'client_key':
                                        key_path = convert_unix_path_to_windows(row['value'], base_path)
                                
                                if cert_path and key_path:
                                    # Convert to Path objects for existence check
                                    cert_path_obj = Path(cert_path)
                                    key_path_obj = Path(key_path)
                                    
                                    # Also try with .crt and .key extensions
                                    if not cert_path_obj.exists():
                                        cert_path_obj = cert_path_obj.with_suffix('.crt')
                                    if not key_path_obj.exists():
                                        key_path_obj = key_path_obj.with_suffix('.key')
                                    
                                    if cert_path_obj.exists() and key_path_obj.exists():
                                        node_pairs.append((node_id, str(cert_path_obj), str(key_path_obj)))
                        except Exception as e:
                            click.echo(click.style(f"Error processing {csv_file}: {str(e)}", fg='yellow'))
        except Exception as e:
            click.echo(click.style(f"Error accessing directory {base_path}: {str(e)}", fg='yellow'))
    else:
        # Original generic search logic
        try:
            # First try CSV method
            for root, dirs, files in os.walk(base_path):
                root_path = Path(root)
                csv_files = [f for f in files if f.endswith('.csv')]
                
                for csv_file in csv_files:
                    csv_path = root_path / csv_file
                    try:
                        with open(csv_path, mode='r') as file:
                            reader = csv.reader(file)
                            node_id = None
                            cert_path = None
                            key_path = None
                            
                            for row in reader:
                                if len(row) < 4:
                                    continue
                                
                                if row[0] == 'node_id':
                                    node_id = row[3]
                                elif row[0] == 'client_cert':
                                    cert_path = row[3]
                                elif row[0] == 'client_key':
                                    key_path = row[3]
                            
                            if node_id and cert_path and key_path:
                                # Convert paths to absolute if they're relative
                                cert_path = Path(cert_path)
                                key_path = Path(key_path)
                                if not cert_path.is_absolute():
                                    cert_path = base_path / cert_path
                                if not key_path.is_absolute():
                                    key_path = base_path / key_path
                                    
                                if cert_path.exists() and key_path.exists():
                                    node_pairs.append((node_id, str(cert_path), str(key_path)))
                    except Exception as e:
                        click.echo(click.style(f"Error processing {csv_file}: {str(e)}", fg='yellow'))

            # If no nodes found via CSV, try direct directory search
            if not node_pairs:
                for root, dirs, files in os.walk(base_path):
                    root_path = Path(root)
                    if root_path.name.startswith("node-"):
                        # Extract node ID from directory name (format: node-XXXXXX-{node_id})
                        if root_path.name.count('-') >= 2:
                            node_id = root_path.name.split('-')[-1]
                            cert_path = root_path / "node.crt"
                            key_path = root_path / "node.key"
                            
                            if cert_path.exists() and key_path.exists():
                                node_pairs.append((node_id, str(cert_path), str(key_path)))
        except Exception as e:
            click.echo(click.style(f"Error accessing directory {base_path}: {str(e)}", fg='yellow'))
    
    return node_pairs

def get_cert_and_key_paths(base_path: str, node_id: str, is_rainmaker: bool = False) -> Tuple[str, str]:
    """Find certificate and key paths for a node."""
    node_pairs = find_node_cert_key_pairs(base_path, is_rainmaker)
    
    for nodeID, cert_path, key_path in node_pairs:
        if str(nodeID) == str(node_id):
            return cert_path, key_path
            
    raise FileNotFoundError(f"Certificate and key not found for node {node_id}")

def get_root_cert_path(config_dir: Path) -> str:
    """Get path to root CA certificate."""
    # First check in config directory
    root_path = config_dir / 'certs' / 'root.pem'
    if root_path.exists():
        return str(root_path)
        
    # Then check in package directory
    package_root = Path(__file__).resolve().parent.parent.parent
    root_path = package_root / 'certs' / 'root.pem'
    if root_path.exists():
        return str(root_path)
        
    raise FileNotFoundError("Root CA certificate not found") 


# ---------------

def convert_unix_path_to_windows(unix_path, base_path):
    """Convert Unix-style path to Windows path relative to base_path."""
    try:
        relative_path = unix_path.split('esp-rainmaker-admin-cli/')[-1]
        return str(Path(base_path) / relative_path)
    except Exception:
        return unix_path


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

def get_cert_paths_from_direct_path(base_path: str, node_id: str) -> Tuple[str, str]:
    """
    Find certificate and key paths for a node when using direct path.
    This is used when --cert-path is provided in CLI.
    
    Args:
        base_path: Base directory to search
        node_id: Node ID to find certificates for
        
    Returns:
        tuple: (cert_path, key_path)
        
    Raises:
        FileNotFoundError: If certificates are not found
    """
    base_path = Path(base_path)
    
    # First try finding in node_details structure
    node_folders = find_node_folders(base_path)
    for folder_node_id, folder_path in node_folders:
        if folder_node_id == node_id:
            crt_path, key_path = find_crt_key_files(folder_path)
            if crt_path and key_path:
                return str(crt_path), str(key_path)
    
    # If not found in node_details, try direct path
    cert_path = base_path / f"{node_id}.crt"
    key_path = base_path / f"{node_id}.key"
    
    if cert_path.exists() and key_path.exists():
        return str(cert_path), str(key_path)
        
    # Try node.crt/node.key in a node-specific directory
    node_dir = base_path / f"node-{node_id}"
    if node_dir.exists():
        cert_path = node_dir / "node.crt"
        key_path = node_dir / "node.key"
        if cert_path.exists() and key_path.exists():
            return str(cert_path), str(key_path)
            
    raise FileNotFoundError(f"Certificate files not found for node {node_id} in {base_path}")
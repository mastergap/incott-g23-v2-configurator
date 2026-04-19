"""
Cross-platform HID interface for Incott G23V2SE mouse.
Abstracts platform-specific details (Linux hidraw, Windows/macOS hidapi).
"""

import os
import sys
import platform

# Platform detection
PLATFORM = sys.platform.lower()
IS_LINUX = PLATFORM.startswith("linux")
IS_WINDOWS = PLATFORM.startswith("win")
IS_MACOS = PLATFORM.startswith("darwin")


class MouseHIDBase:
    """Base class for HID implementations."""
    
    def __init__(self, vendor_id, product_ids):
        self.vendor_id = vendor_id
        self.product_ids = product_ids
        self.device = None
        
    def find_device(self):
        """Find and return (device_path, product_id) tuple. Implement in subclass."""
        raise NotImplementedError
        
    def open(self, device_path):
        """Open the device. Implement in subclass."""
        raise NotImplementedError
        
    def close(self):
        """Close the device."""
        raise NotImplementedError
        
    def send_feature_report(self, data):
        """Send a feature report. Implement in subclass."""
        raise NotImplementedError
        
    def read(self, size=64):
        """Read data from device. Implement in subclass."""
        raise NotImplementedError


class LinuxMouseHID(MouseHIDBase):
    """Linux implementation using hidraw and fcntl."""
    
    def __init__(self, vendor_id, product_ids):
        super().__init__(vendor_id, product_ids)
        self.fd = None
        import glob
        import fcntl
        self.glob = glob
        self.fcntl = fcntl
        
    def HIDIOCSFEATURE(self, length):
        """Compute ioctl code for feature reports."""
        return 0xC0004806 | (length << 16)
    
    def find_device(self):
        """Find the mouse on Linux by scanning /sys/class/hidraw.
        Returns (device_path, product_id) or (None, None)."""
        candidates = []
        vid_str = f"{self.vendor_id:04x}"
        
        for path in self.glob.glob("/sys/class/hidraw/hidraw*/device"):
            try:
                with open(os.path.join(path, "uevent"), "r") as f:
                    content = f.read()
                    if vid_str in content.lower():
                        node_name = path.split('/')[-2]
                        
                        # Extract product ID from HID_ID line
                        # Format: HID_ID=0003:0000093A:0000622C (type:VID:PID)
                        pid = None
                        for line in content.split('\n'):
                            if 'HID_ID=' in line:
                                # Extract the PID (third part after colons)
                                parts = line.split('=')[1].strip().split(':')
                                if len(parts) >= 3:
                                    pid = int(parts[2], 16)
                                break
                        
                        candidates.append((f"/dev/{node_name}", pid))
            except Exception:
                continue
        
        # Return the last (highest interface) for management node
        if candidates:
            return candidates[-1]
        return None, None
    
    def open(self, device_path):
        """Open hidraw device."""
        try:
            self.fd = os.open(device_path, os.O_RDWR | os.O_NONBLOCK)
            return True
        except PermissionError:
            raise PermissionError(f"Access Denied to {device_path}. Check permissions.")
        except Exception as e:
            raise Exception(f"Failed to open {device_path}: {e}")
    
    def close(self):
        """Close hidraw device."""
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
    
    def send_feature_report(self, data):
        """Send feature report via ioctl."""
        if self.fd is None:
            raise RuntimeError("Device not open")
        if isinstance(data, list):
            data = bytes(data)
        self.fcntl.ioctl(self.fd, self.HIDIOCSFEATURE(len(data)), data)
    
    def read(self, size=64):
        """Read from device (non-blocking)."""
        if self.fd is None:
            raise RuntimeError("Device not open")
        try:
            return os.read(self.fd, size)
        except BlockingIOError:
            return b''


class HIDAPIMouseHID(MouseHIDBase):
    """Cross-platform implementation using hidapi library."""
    
    def __init__(self, vendor_id, product_ids):
        super().__init__(vendor_id, product_ids)
        try:
            import hid
            self.hid = hid
        except ImportError:
            raise ImportError("hidapi not installed. Run: pip install hidapi")
        self.device_handle = None
    
    def find_device(self):
        """Find mouse using hidapi enumeration.
        Returns (device_path, product_id) or (None, None)."""
        devices = self.hid.enumerate()
        candidates = []
        
        for dev in devices:
            if dev['vendor_id'] == self.vendor_id:
                candidates.append((dev['path'], dev['product_id']))
        
        if not candidates:
            return None, None
        
        # Return the last (highest interface) for management
        return candidates[-1]
    
    def open(self, device_path):
        """Open device via hidapi."""
        try:
            self.device_handle = self.hid.device()
            self.device_handle.open_path(device_path)
            self.device_handle.set_nonblocking(True)
            return True
        except Exception as e:
            raise Exception(f"Failed to open device: {e}")
    
    def close(self):
        """Close hidapi device."""
        if self.device_handle is not None:
            self.device_handle.close()
            self.device_handle = None
    
    def send_feature_report(self, data):
        """Send feature report via hidapi."""
        if self.device_handle is None:
            raise RuntimeError("Device not open")
        if isinstance(data, bytes):
            data = list(data)
        self.device_handle.send_feature_report(data)
    
    def read(self, size=64):
        """Read from device."""
        if self.device_handle is None:
            raise RuntimeError("Device not open")
        try:
            result = self.device_handle.read(size)
            return bytes(result) if result else b''
        except Exception:
            return b''


def create_mouse_hid(vendor_id, product_ids):
    """Factory function to create platform-appropriate HID handler."""
    if IS_LINUX:
        return LinuxMouseHID(vendor_id, product_ids)
    else:
        # Fall back to hidapi for Windows/macOS
        return HIDAPIMouseHID(vendor_id, product_ids)

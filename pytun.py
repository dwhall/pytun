"""pytun

Creates and manages tun/tap tunnels on Linux.
"""

__author__ = "Gawen Arab"
__copyright__ = "Copyright 2012, Gawen Arab"
__credits__ = ["Gawen Arab", "Ben Lapid"]
__license__ = "MIT"
__version__ = "1.0.1"
__maintainer__ = "Gawen Arab"
__email__ = "g@wenarab.com"
__status__ = "Beta"

import os
import fcntl
import socket
import struct
import logging
import functools


logger = logging.getLogger("pytun")


class Tunnel():
    """tun/tap handler class """

    class AlreadyOpened(Exception):
        """Raised when the user try to open a already-opened
        tunnel.
        """
        pass

    class PermissionDenied(Exception):
        """Raised when pytun try to setup a new tunnel without
        the good permissions.
        """
        pass

    MODES = {
        "tun": 0x0001,
        "tap": 0x0002,
    }

    # No packet information flag
    IFF_NO_PI = 0x1000

    # ioctl call
    TUNSETIFF = 0x400454ca
    SIOCSIFHWADDR = 0x8924
    SIOCSIFADDR = 0x8916
    SIOCSIFFLAGS = 0x8914
    IFF_UP          = 0x1
    IFF_POINTOPOINT = 0x10
    IFF_RUNNING     = 0x40
    IFF_NOARP       = 0x80
    IFF_MULTICAST   = 0x1000

    def __init__(self, mode="tun", pattern="", auto_open=True, no_pi=False, tun_path="/dev/net/tun"):
        """Creates a new tun/tap tunnel. Its type is defined by the
        argument 'mode' whose value can be either a string or
        the system value.

        The argument 'pattern' sets the string format used to
        generate the name of the future tunnel. By default, for
        Linux, it is "tun%d" or "tap%d" depending on the mode.

        If the argument 'auto_open' is true, this constructor
        will automatically create the tunnel.

        If the argument 'no_pi' is true, the device will be
        be opened with the IFF_NO_PI flag. Otherwise, 4 extra
        bytes are added to the beginning of the packet (2 flag
        bytes and 2 protocol bytes).
        """
        super().__init__()

        self.pattern = pattern
        self.mode = mode
        self.no_pi = self.IFF_NO_PI if no_pi else 0x0000
        self.tun_path = tun_path
        self.name = None
        self.fd = None

        if isinstance(self.mode, str):
            self.mode = self.MODES.get(self.mode, None)
            assert self.mode is not None, "%r is not a valid tunnel type." % (self.mode, )

        if auto_open:
            self.open()

    def __del__(self):
        self.close()

    @property
    def mode_name(self):
        """Returns the tunnel mode's name, for printing purpose."""
        for name, id in self.MODES.items():
            if id == self.mode:
                return name

    def fileno(self):
        return self.fd

    def open(self):
        """Creates the tunnel.
        If the tunnel is already opened, the function will
        raise an AlreadyOpened exception.
        """
        if self.fd is not None:
            raise self.AlreadyOpened()
        logger.debug(f"Opening {self.tun_path}...")
        self.fd = os.open(self.tun_path, os.O_RDWR)
        logger.debug(f"Opening {self.mode_name.upper()} tunnel '{self.pattern}'...")
        try:
            ret = fcntl.ioctl(self.fd, self.TUNSETIFF, struct.pack("16sH", self.pattern.encode(), self.mode | self.no_pi))

        except IOError as e:
            if e.errno == 1:
                logger.error(f"Cannot open a {self.mode_name.upper()} tunnel because the operation is not permitted.")
                raise self.PermissionDenied()

            raise
        self.name = ret[:16].strip(b"\x00").decode()
        logger.info(f"Tunnel '{self.name}' opened.")

    def close(self):
        if self.fd:
            os.close(self.fd)
            self.fd = None
            logger.info(f"Tunnel '{self.name}' closed.")

    def send(self, buf):
        return os.write(self.fd, buf)

    def recv(self, size=1500):
        return os.read(self.fd, size)

    def set_mac(self, mac):
        """Sets the MAC address of the device to 'mac'.
        parameter 'mac' should be a binary representation
        of the MAC address
        Note: Will fail for TUN devices
        """
        mac = map(ord, mac)
        ifreq = struct.pack('16sH6B8', self.name, socket.AF_UNIX, *mac)
        fcntl.ioctl(self.fileno(), self.SIOCSIFHWADDR, ifreq)

    def set_ipv4(self, ip):
        """Sets the IP address (ifr_addr) of the device
        parameter 'ip' should be string representation of IP address
        This does the same as ifconfig.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bin_ip = socket.inet_aton(ip)
        ifreq = struct.pack('16sH2s4s8s', self.name, socket.AF_INET, '\x00'*2, bin_ip, '\x00'*8)
        fcntl.ioctl(sock, self.SIOCSIFADDR, ifreq)
        ifreq = struct.pack('16sH', self.name, self.IFF_UP|self.IFF_POINTOPOINT|self.IFF_RUNNING|self.IFF_MULTICAST)
        fcntl.ioctl(sock, self.SIOCSIFFLAGS, ifreq)


    def __repr__(self):
        return f"<{self.mode_name.capitalize()} tunnel '{self.name}'>"

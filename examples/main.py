import logging
import select

import pytun


def pprint_in_hex(buf):
    DEFAULT_SIZE = 4

    def hex2(i, l=None):
        l = l if l is not None else DEFAULT_SIZE

        h = hex(i).upper()[2:]

        if len(h) != l:
            h = "0" * (l - len(h)) + h

        return h

    def displayable_char(c):
        if ord(c) < 0x20 or ord(c) >= 0x7f:
            c = "."

        return c

    print(" " * DEFAULT_SIZE, end=' ')
    for i in range(16): print(hex2(i, 2), end=' ')
    print()

    raws = []
    for i, c in enumerate(buf):
        if i % 16 == 0:
            if i:
                print("\t" + "".join(raws))
                raws = []

            print(hex2(i), end=' ')
        raws.append(displayable_char(c))

        print(hex2(ord(c), 2), end=' ')

    print("  " * (15 - (i % 16)) + "\t" + "".join(raws))


def main():
    pytun.logger.setLevel(logging.DEBUG)
    logging.basicConfig()

    try:
        tun = pytun.Tunnel()

    except pytun.Tunnel.PermissionDenied:
        print("*" * 80)
        print(f"You do not have the privileges to access {tun.tun_path}.\n"
              "Give the access of this file to pytun, or\n"
              "elevate this current script to root level.")
        print("*" * 80)
        raise

    print("*" * 80)
    print(f"The tunnel '{tun.name}' had been created.\n"
          "If you want to play with it, first configure it.\n"
          "1. Set up the network and set an IP\n"
          f"    $ ifconfig {tun.name} 192.168.42.1\n"
          "2. Add the network route\n"
          f"    $ route add -net 192.168.42.0/24 dev {tun.name}\n"
          "Then, try to ping some IP in this network ...\n"
          "    $ ping 192.168.42.42\n"
          "Or do some UDP netcat magic.\n"
          "    $ nc 192.168.42.42 4242 -u\n")
    print("*" * 80)

    try:
        # Receive loop
        while True:
            buf = tun.recv()

            pytun.logger.info("Packet received")
            pprint_in_hex(buf)
            print()

    except KeyboardInterrupt:
        pass

    finally:
        tun.close()
        print("Closed.")


if __name__ == "__main__":
    main()

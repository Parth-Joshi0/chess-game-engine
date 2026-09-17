"""UCI entry point: `python uci.py`.

Wires stdin/stdout to UciProtocol and nothing else. Point a chess GUI at this file:

    cutechess-cli -engine cmd=python3 arg=/path/to/uci.py proto=uci ...

Keep this thin -- the protocol lives in uci_protocol.py and the engine orchestration
in engine_session.py, so a web backend can import those without going near stdin.
"""

import sys

from uci_protocol import UciProtocol


def main() -> int:
    protocol = UciProtocol(lambda line: print(line, flush=True))

    # Read line by line rather than iterating the file object, which would buffer and
    # stall the handshake.
    while not protocol.quitting:
        line = sys.stdin.readline()
        if not line:  # EOF: the GUI closed the pipe
            break
        protocol.handle_line(line.strip())

    protocol.session.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())

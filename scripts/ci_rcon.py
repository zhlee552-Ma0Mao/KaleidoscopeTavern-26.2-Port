import socket, struct, sys

HOST, PORT, PASSWORD = "127.0.0.1", 25575, "ci"

def packet(req_id, kind, body):
    payload = struct.pack("<ii", req_id, kind) + body.encode() + b"\x00\x00"
    return struct.pack("<i", len(payload)) + payload

def recv_packet(sock):
    n = struct.unpack("<i", sock.recv(4))[0]
    data = b""
    while len(data) < n:
        data += sock.recv(n - len(data))
    return struct.unpack("<ii", data[:8]), data[8:-2].decode(errors="replace")

with socket.create_connection((HOST, PORT), timeout=10) as s:
    s.sendall(packet(1, 3, PASSWORD))
    (rid, _), _ = recv_packet(s)
    if rid == -1:
        raise SystemExit("RCON authentication failed")
    command = " ".join(sys.argv[1:])
    s.sendall(packet(2, 2, command))
    (rid, _), body = recv_packet(s)
    if rid != 2:
        raise SystemExit("Unexpected RCON response")
    print(body)

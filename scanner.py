import argparse
import ipaddress
import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor

def is_lab(host: str):
    ip = ipaddress.ip_address(socket.gethostbyname(host))
    return ip.is_loopback or ip.is_private

def parse_port(spec: str):
    ports = set()
    for part in spec.split(','):
        if '-' in part:
            a,b = part.split('-')
            ports.update(range(int(a), int(b) + 1))
        else:
            ports.add(int(part))
    return sorted(p for p in ports if 0<p<65536)

def scan_port(host: str, port: int, timeout: float):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        if s.connect_ex((host, port)) != 0:
            return None
        try:
            service = socket.getservbyport(port, 'tcp')
        except OSError:
            service = 'unknown'
        return {'port': port, 'state': 'open', 'service': service}

def main():
    ap = argparse.ArgumentParser(description='TCP Port Scanner')
    ap.add_argument('host', help='target, e.g. 127.0.0.1')
    ap.add_argument('-p', '--ports', default='1-1024', help='e.g. 22, 80, 8000-8100')
    ap.add_argument('-t', '--threads', type=int, default=100)
    ap.add_argument('--timeout', type=float, default=0.5)
    ap.add_argument('-o', '--output', help='result will saved to JSON file')
    args = ap.parse_args()

    if not is_lab(args.host):
        raise SystemExit('[!] Only practical lab are allowed.')

    ports = parse_port(args.ports)
    print(f'[*] Scanning {args.ports} ({len(ports)} ports)...')
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        results = [r for r in ex.map(lambda p: scan_port(args.host, p, args.timeout), ports) if r]

    elapsed = time.perf_counter() - start
    print(f'{'PORT':<8}{'STATE':<8}SERVICE')
    for r in results:
        print(f'{r['port']:<8}{r['state']:<8}{r['service']}')
    print(f'[*] Done in {elapsed:.2f}s, {len(results)} open ports')

    if args.output:
        with open(args.output, 'w') as f:
            json.dump({'host': args.host, 'scanned': len(ports),
                       'elapsed_sec': round(elapsed, 2), 'open': results}, f, indent=2)
        print(f'[*] Saved to {args.output}')

if __name__ == '__main__':
    main()
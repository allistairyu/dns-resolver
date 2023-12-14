import dns.message
import dns.query
import socket
from cachetools import Cache, TTLCache
import csv
import random
from ipaddress import ip_address, IPv4Address 
import time
import argparse

# https://stackoverflow.com/questions/53405470/python-cachetools-can-items-have-different-ttl
class TTLItemCache(TTLCache):
    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__, ttl=None):
        super(TTLItemCache, self).__setitem__(key, value)
        if ttl:
            link = self._TTLCache__links.get(key, None)
            if link:
                link.expires += ttl - self.ttl


root_servers = ['198.41.0.4', '170.247.170.2', '192.33.4.12', '199.7.91.13', 
				'192.203.230.10', '192.5.5.241', '192.112.36.4', '198.97.190.53',
				'192.36.148.17', '192.58.128.30', '193.0.14.129','199.7.83.42',
				'202.12.27.33']


def main(query_type, verbose):
	cache = TTLItemCache(maxsize=4096, ttl=100)
	dns_servers = loadDNSServers()
	while True:
		domain = input('Enter a domain name to query: ')
		print('Querying for ' + domain + '...')
		start = time.time()
		cached = False
		if query_type == 'recursive':
			answer, cached = recursiveQuery(domain, cache, dns_servers)
			print(answer)
		elif query_type == 'iterative':
			answer, cached, path = iterativeQuery(domain, cache)
			print(answer)

		end = time.time()
		if verbose and answer != 'Unable to find domain':
			print('-----------------------------------------------------------')
			print('{:>12}  {:<45}'.format('Time (ms): ', str(100 * (end - start))))
			print('{:>12}  {:<45}'.format('Cached? ', str(cached)))
			if query_type == 'iterative':
				print('{:>12}  {:<65}'.format('Path: ', ' --> '.join(path)))
			print('-----------------------------------------------------------')


def recursiveQuery(domain, cache, dns_servers):
	if domain in cache:
		return cache[domain], True
	
	query = createDNSPacket(domain)
	port = 53

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP

	# pick a public nameserver to query (random? idk)
	r = list(range(50))
	random.shuffle(r)
	# TODO: how many servers should we check? also implement
	# multithreading/processing if have time
	for i in r:
		addr = dns_servers[i]
		if type(ip_address(addr)) is not IPv4Address:
			continue
		try:
			sock.sendto(query, (addr, port))
			sock.settimeout(3)
			response = sock.recv(1024)
			response = dns.message.from_wire(response)
			sock.close()
			answer = response.answer[0]
			cache.__setitem__(domain, answer, ttl=answer.ttl)
			return answer, False
		except socket.timeout:
			print('timed out. trying another dns server...')
		except IndexError:
			break
	return "Unable to find domain", False


def iterativeQuery(domain, cache):
	if domain in cache:
		return cache[domain], True, []

	query = createDNSPacket(domain)
	# start with root server
	addr = root_servers[0]
	index = 1
	port = 53
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
	tries = 0
	path = []
	while tries < 50:
		try:
			sock.sendto(query, (str(addr), port))
			sock.settimeout(3)
			responseBytes, sender = sock.recvfrom(1024)
			path.append(sender[0])
			response = dns.message.from_wire(responseBytes)
			if len(response.answer) == 0:
				# get first ipv4 address. better solution?
				for a in response.additional:
					if a.rdtype == 1:
						addr = a[0].address
						break
					
				else:
					addr = root_servers[index]
					path = []
					print('going to next root server')
					index += 1
			else:
				answer = response.answer[0]
				cache.__setitem__(domain, answer, ttl=answer.ttl)
				return answer, False, path
			tries += 1
		except socket.timeout:
			addr = root_servers[index]
			path = []
			index += 1
		except Exception as e:
			break
	
	sock.close()
	return "Unable to find domain", False, []

def createDNSPacket(query):
	query_message = dns.message.make_query(query, 1) # 1 for record type A
	return query_message.to_wire()
	
def loadDNSServers():
	dns_servers = []
	# load 50 dns server addresses in from file
	with open('us.csv', newline='') as csvfile:
		reader = csv.reader(csvfile, delimiter=' ')
		next(reader, None)
		i = 0
		for row in reader:
			addr = row[0][:row[0].index(",")]
			dns_servers.append(addr)
			i += 1
			if i == 50: # 50 should be enough?
				break
	return dns_servers

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='DNS resolver that supports iterative and recursive queries')
	parser.add_argument('--method', type=str,
						help='recursive/iterative. default is recursive.')
	parser.add_argument('--verbose', action='store_true',
						help='print additional information for each query.')	
	args = parser.parse_args()
	method = args.method
	if method:
		if args.method not in ('recursive', 'iterative'):
			parser.error('Invalid query type. Must be recursive or iterative.')
	else:
		method = 'recursive'
	main(method, args.verbose)

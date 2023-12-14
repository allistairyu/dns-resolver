import dns.message
import dns.query
import socket
from cachetools import Cache, TTLCache
import csv
from ipaddress import ip_address, IPv4Address 
import time
import argparse
import threading

# https://stackoverflow.com/questions/53405470/python-cachetools-can-items-have-different-ttl
class TTLItemCache(TTLCache):
    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__, ttl=None):
        super(TTLItemCache, self).__setitem__(key, value)
        if ttl:
            link = self._TTLCache__links.get(key, None)
            if link:
                link.expires += ttl - self.ttl

# https://stackoverflow.com/questions/10525185/python-threading-how-do-i-lock-a-thread
class Thread(threading.Thread):
    def __init__(self, t, *args):
        threading.Thread.__init__(self, target=t, args=args)
        self.start()
lock = threading.Lock()

root_servers = ['198.41.0.4', '170.247.170.2', '192.33.4.12', '199.7.91.13', 
				'192.203.230.10', '192.5.5.241', '192.112.36.4', '198.97.190.53',
				'192.36.148.17', '192.58.128.30', '193.0.14.129','199.7.83.42',
				'202.12.27.33']
cache = TTLItemCache(maxsize=4096, ttl=100)
rdtypes = {"A" : 1, "AAAA": 28, "TXT": 16, "ANY" : 0}


def main(query_type, verbose):
	dns_servers = loadDNSServers()
	while True:
		# parse input
		query = input('Enter a <domain name> [record type] to query (\'q\' to quit): ')
		if query == "q":
			return
		elif query == "":
			continue
		tokens = query.split(' ')
		domain = tokens[0]
		rd = "A"
		if len(tokens) > 1:
			rd = tokens[1]
		if rd not in rdtypes:
			print("Not a valid record type: must be one of \"A\", \"AAAA\", \"TXT\" (or \"ANY\" to get all).")
			continue
		
		print('Querying for ' + domain + '...')
		to_query = [rd] # list of types to query, mainly for ANY option
		cached = False
		if rd == "ANY":
			to_query = ["A", "AAAA", "TXT"]
		msg = False
		for idx in to_query:
			start = time.time()
			if query_type == 'recursive':
				answer, cached = recursiveQuery(domain, dns_servers, idx)
			elif query_type == 'iterative':
				answer, cached, path = iterativeQuery(domain, idx)
			if rd != "ANY" or answer != "Unable to find domain":
				print(answer)
				msg = True
			end = time.time()
			if verbose and answer != 'Unable to find domain': # if ANY, don't print if not found; do at end
				net = "%.3f" % (1000 * (end - start))
				print('-----------------------------------------------------------')
				print('{:>12}  {:<45}'.format('Time (ms): ', net))
				print('{:>12}  {:<45}'.format('Cached? ', str(cached)))
				if query_type == 'iterative':
					print('{:>12}  {:<65}'.format('Path: ', ' --> '.join(path)))
				print('-----------------------------------------------------------')
		if rd == "ANY" and not msg: # in the case that ANY doesn't find anything, indicating domain not found (but these msgs weren't printed before)
			print("Unable to find domain")

def queryCache(cache_domain): # given cache key returns value, if it exists
	if cache_domain in cache:
		return cache[cache_domain], True
	else:
		return None, False

def dnsServerThread(query, sock, addr, cache_key, event): # thread for querying from server
	port = 53
	if type(ip_address(addr)) is not IPv4Address:
		return
	try:
		sock.sendto(query, (addr, port))
		sock.settimeout(3)
		response = sock.recv(1024)
		response = dns.message.from_wire(response)
		sock.close()
		lock.acquire()
		try: 
			if not event.is_set(): # no answer has been found yet, set it in cache
				answer = response.answer[0]
				cache.__setitem__(cache_key, answer, ttl=answer.ttl)
				event.set()
				return
			else:
				lock.release()
				return
		finally:
			lock.release()
	finally:
		return

def recursiveQuery(domain, dns_servers, rdtype):
	event = threading.Event()
	cache_domain = str(domain) + " " + rdtype
	cache_ans, cached = queryCache(cache_domain)
	if cached: # already cached, just return
		return cache_ans, True
	
	query = createDNSPacket(domain, rdtype)

	r = list(range(len(dns_servers)))

	thread_list = []
	for i in r: # start the threads
		addr = dns_servers[i]
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
		thread_list.append(Thread(dnsServerThread, query, sock, addr, cache_domain, event))
	
	event.wait(timeout = 3) # wait for at most 3 sec
	if event.is_set():
		return cache[cache_domain], False
	else:
		return "Unable to find domain", False


def iterativeQuery(domain, rdtype):
	cache_domain = str(domain) + " " + rdtype
	if cache_domain in cache:
		return cache[cache_domain], True, []
	query = createDNSPacket(domain, rdtype)

	# start with root server
	addr = root_servers[0]
	index = 1
	port = 53
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
	depth = 0
	path = []
	while depth < 8:
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
				else: # check authority section for name servers
					if len(response.authority) > 0 and len(response.authority[0]) > 0:
						next_domain = response.authority[0][0]
						answer, _, path = iterativeQuery(next_domain, rdtype)
						if answer != 'Unable to find domain':
							cache.__setitem__(cache_domain, answer, ttl=answer.ttl)
						sock.close()
						return answer, False, path
					else: 
						addr = root_servers[index]
						path = []
						index += 1
						depth = 0
						if index == len(root_servers): 
							depth = 8
			else:
				answer = response.answer[0]
				cache.__setitem__(cache_domain, answer, ttl=answer.ttl)
				sock.close()
				return answer, False, path
			depth += 1
		except socket.timeout:
			addr = root_servers[index]
			path = []
			index += 1
			depth = 0
			if index == len(root_servers):
				depth = 8
		except Exception as e:
			print(e)
			break
	
	sock.close()
	return "Unable to find domain", False, []

def createDNSPacket(query, rdtype="A"):
	query_message = dns.message.make_query(query, rdtypes[rdtype]) # 1 for record type A
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

import sys
import dns.message
import dns.query
import socket
from cachetools import cached, TTLCache

root_server = '198.41.0.4'

def main(query_type='recursive'):
	while True:
		# domain = input('Enter a domain name to query: ')
		domain = 'cs.brown.edu'
		print('Querying for ' + domain)
		query = createDNSPacket(domain)
		if query_type == 'recursive':
			recursiveQuery(query)
		elif query_type == 'iterative':
			iterativeQuery(query)
		break

# this by itself might just work. need to test tho
@cached(cache=TTLCache(maxsize=1024, ttl=600))
def recursiveQuery(query):
	# pick a public nameserver to query (random? idk)
	# 204.106.240.53
	ip = '204.106.240.53'
	port = 53

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
	try:
		sock.sendto(query, (ip, port))
		response = sock.recv(1024)
		response = dns.message.from_wire(response)
		print(response)
	except Exception as e:
		print(e)
	sock.close()


@cached(cache=TTLCache(maxsize=1024, ttl=600))
def iterativeQuery(query):
	# query root server
	port = 53

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
	try:
		sock.sendto(query, (root_server, port))
		response = sock.recv(1024)
		response = dns.message.from_wire(response)
		print(response)
	except Exception as e:
		print(e)
	sock.close()

def createDNSPacket(query):
	query_message = dns.message.make_query(query, 28)
	return query_message.to_wire()

def parseResponse(response):
	pass
	

if __name__ == "__main__":
	query_type = sys.argv[1]
	if query_type not in ('recursive', 'iterative'):
		raise ValueError('Invalid query type. Must be recursive or iterative.')
	main(query_type)
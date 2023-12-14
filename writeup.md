
## Introduction
Domain Name System (DNS) translates human-readable domain names into IP
addresses. In this project, we created a simple DNS resolver using Python. We
minimally relied on the dnspython library to serialize and deserialize queries.

## Design/Implementation

#### Overall
Our `main` function parses user input for a domain and a record type. If no
flags were passed into the command line, the resolver defaults to
recursive queries with the `recursiveQuery` function. If the
`--iterative` flag is passed in, `iterativeQuery` is called. To convert a domain
into a query, we use the `dns.message.make_query` function. To then serialize it
for sending over a UDP socket, we use `dns.message.Message.to_wire` method.

#### Global variables
- `lock`: a `threading.Lock` to ensure only one thread for `recursiveQuery`
  returns a result
- `root_servers`: a hard-coded list of all 13 root servers
- `cache`: a `TTLItemCache`, which inherits from `TTLCache`, allowing for each
  item to have its own TTL
- `rdtypes`: a dictionary mapping from record types to their equivalent in the
  `dnspython` library

#### `recursiveQuery`
*Takes in a domain, list of DNS servers, and a record type. Returns address (or
error message) and a boolean representing whether the result was cached.*

If the domain is in the cache, the cached result is returned. Otherwise, we rely
on multithreading to query multiple DNS servers. Concretely, we create a thread 
for each DNS server passed in. Each thread runs `dnsServerThread`, which queries
the given DNS server via a UDP socket for an answer. The first thread that 
receives an answer acquires the lock and stores the answer in the cache with the
TTL from the answer. The original `recursiveQuery` thread simply waits until one
of its threads sets an answer and returns. If no threads were able to receive a
response, "Unable to find domain" is returned.

#### `iterativeQuery`
*Takes in a domain and a record type. Returns address (or error message),
a boolean representing whether the result was cached, and the path that the
iterative algorithm took.*

If the domain is in the cache, the cached result is returned. Otherwise, the
iterative algorithm proceeds. The first root server is queried via a UDP socket.
When we receive a response, if an additional section exists, we continue to
iterate with an address from the additional section. Otherwise, we continue with
a nameserver from the authority section. If a particular root server is not able
to eventually resolve a domain, we try a different root server. If we do
receive an answer, we store it in the cache with the answer's TTL and return
the address (or "Unable to find domain") and the path taken.

## Discussion/Results



## Conclusions/Future Work
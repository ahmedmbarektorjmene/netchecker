from dnslib import DNSRecord, RR, A, QTYPE
from dnslib.server import DNSServer, BaseResolver


class LocalResolver(BaseResolver):
    def resolve(self, request, handler):
        qname = str(request.q.qname)
        reply = request.reply()
        # Override any real domain you want:
        if qname.endswith("netflix.com") or qname.endswith("www.netflix.com") or qname.endswith("www.netflix.com.") or qname.endswith("netflix.com."):
            reply.add_answer(RR(qname, QTYPE.A, rdata=A("127.0.0.1"), ttl=60))
        else:
            # Optional: forward to real DNS for everything else
            import dns.resolver

            try:
                answers = dns.resolver.resolve(qname[:-1], "A")
                for rdata in answers:
                    reply.add_answer(RR(qname, QTYPE.A, rdata=A(rdata.address), ttl=60))
            except Exception:
                pass
        return reply


resolver = LocalResolver()
server = DNSServer(resolver, port=53, address="127.0.0.1")
print("Local DNS server running on 127.0.0.1:53")
server.start()

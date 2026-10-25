"""Disiscrizione in un clic (RFC 8058): POST al link del mittente, con i controlli sul link.
Solo https verso indirizzi pubblici di internet: niente http, niente reti locali (router, stampanti,
servizi del computer), e lo stesso vale per ogni redirect. Nessun cookie, nessun dato dell'utente."""
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request

from tkiscrizioni import VERSION

MAX_REDIRECT = 3


class LinkNonAmmesso(Exception):
    pass


def host_pubblico(host):
    """Vero se il nome (o l'indirizzo) porta solo a indirizzi pubblici di internet."""
    host = (host or "").strip().strip("[]")
    if not host:
        return False
    try:
        indirizzi = [ipaddress.ip_address(host.split("%")[0])]
    except ValueError:
        try:
            info = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        except (socket.gaierror, UnicodeError, OSError):
            return False
        indirizzi = []
        for i in info:
            try:
                indirizzi.append(ipaddress.ip_address(str(i[4][0]).split("%")[0]))
            except ValueError:
                return False
    if not indirizzi:
        return False
    for ip in indirizzi:
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            return False
    return True


def url_ammesso(url, consenti=host_pubblico):
    """https, con un host, che porta a un indirizzo pubblico."""
    try:
        p = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    return p.scheme.lower() == "https" and bool(p.hostname) and consenti(p.hostname)


def host_di(url):
    """Host del link https (o dell'indirizzo mailto) da mostrare all'utente."""
    if (url or "").lower().startswith("mailto:"):
        return url[7:].split("?")[0].rpartition("@")[2].strip().lower()
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


class _Redirect(urllib.request.HTTPRedirectHandler):
    max_redirections = MAX_REDIRECT

    def __init__(self, consenti):
        super().__init__()
        self.consenti = consenti

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        newurl = urllib.parse.urljoin(req.full_url, newurl)
        if not url_ammesso(newurl, self.consenti):
            raise LinkNonAmmesso(f"il mittente rimanda a un indirizzo non sicuro ({host_di(newurl) or newurl})")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def invia(url, timeout=20, contesto=None, consenti=host_pubblico):
    """Manda «List-Unsubscribe=One-Click». Ritorna il codice HTTP; solleva LinkNonAmmesso o l'errore di rete."""
    if not url_ammesso(url, consenti):
        raise LinkNonAmmesso(f"il link non è sicuro ({host_di(url) or url}): serve https verso un sito pubblico")
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=contesto), _Redirect(consenti))
    req = urllib.request.Request(url, data=b"List-Unsubscribe=One-Click", method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded",
                                          "User-Agent": f"tk-iscrizioni/{VERSION}"})
    with opener.open(req, timeout=timeout) as resp:
        return resp.status

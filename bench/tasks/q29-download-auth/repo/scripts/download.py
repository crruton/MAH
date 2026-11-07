import netrc


def credentials(path=".netrc"):
    n = netrc.netrc(path)
    login, _, password = n.authenticators("example.com")
    return login, password

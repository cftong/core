"""
Classes and functions for managing LDAP domains.

arkOS Core
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import ldap
import ldap.modlist

from arkos import config, conns, signals
from arkos.system import users
from arkos.utilities import b, errors


class Domain:
    """Class for managing arkOS domains in LDAP."""

    def __init__(self, name, rootdn="dc=arkos-servers,dc=org"):
        """
        Initialize the domain object.

        :param str name: domain name
        :param str rootdn: Associated root DN in LDAP
        """
        self.name = name
        self.rootdn = rootdn

    def __str__(self):
        """Domain name."""
        return self.name

    @property
    def ldap_id(self):
        """Fetch LDAP ID."""
        qry = "virtualdomain={0},ou=domains,{1}"
        return qry.format(self.name, self.rootdn)

    def add(self):
        """Add the domain to LDAP."""
        try:
            ldif = conns.LDAP.search_s(self.ldap_id, ldap.SCOPE_SUBTREE,
                                       "(objectClass=*)", None)
            emsg = "This domain is already present here"
            raise errors.InvalidConfigError(emsg)
        except ldap.NO_SUCH_OBJECT:
            pass
        ldif = {"virtualdomain": [b(self.name)],
                "objectClass": [b"mailDomain", b"top"]}
        signals.emit("domains", "pre_add", self)
        conns.LDAP.add_s(self.ldap_id, ldap.modlist.addModlist(ldif))
        signals.emit("domains", "post_add", self)

    def remove(self):
        """Delete domain."""
        if self.name in [x.domain for x in users.get()]:
            emsg = "A user is still using this domain"
            raise errors.InvalidConfigError(emsg)
        signals.emit("domains", "pre_remove", self)
        conns.LDAP.delete_s(self.ldap_id)
        signals.emit("domains", "post_remove", self)

    @property
    def as_dict(self, ready=True):
        """Return domain metadata as dict."""
        return {"id": self.name, "is_ready": ready}

    @property
    def serialized(self):
        """Return serializable domain metadata as dict."""
        return self.as_dict


def get(id=None):
    """
    Get all domains.

    :param str id: domain name to fetch
    :returns: Domain(s)
    :rtype: Domain or list thereof
    """
    results = []
    qset = conns.LDAP.search_s(
        "ou=domains,{0}".format(config.get("general", "ldap_rootdn")),
        ldap.SCOPE_SUBTREE, "(virtualdomain=*)", ["virtualdomain"])
    for x in qset:
        d = Domain(x[1]["virtualdomain"][0].decode(),
                   x[0].split("ou=domains,")[1])
        if d.name == id:
            return d
        results.append(d)
    return results if id is None else None

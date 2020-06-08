from bip32utils import BIP32Key


def minutes_since_epoch(begin):
    """
    :param datetime.datetime begin:
    :rtype: int
    """
    return int(begin.replace(second=0, microsecond=0).timestamp())


class KeyGenerator(object):
    """
    Generates ledger keys for various object types.
    These are the keys used when encrypting blocks on the ledger.
    """

    @staticmethod
    def get_key_for_user(user):
        """
        :param origin.auth.User user:
        :rtype: BIP32Key
        """
        return BIP32Key.fromExtendedKey(user.master_extended_key)

    @staticmethod
    def set_key_for_user(user, key):
        """
        :param origin.auth.User user:
        :param BIP32Key key:
        """
        user.master_extended_key = key.ExtendedKey()

    @staticmethod
    def set_key_for_user_from_entropy(user, entropy):
        """
        :param origin.auth.User user:
        :param bytes entropy:
        """
        KeyGenerator.set_key_for_user(
            user, BIP32Key.fromEntropy(entropy))

    @staticmethod
    def get_key_for_metering_point(meteringpoint):
        """
        :param origin.auth.MeteringPoint meteringpoint:
        :rtype: BIP32Key
        """
        return KeyGenerator \
            .get_key_for_user(meteringpoint.user) \
            .ChildKey(1) \
            .ChildKey(meteringpoint.key_index)

    @staticmethod
    def get_key_for_measurement(meteringpoint, begin):
        """
        :param origin.auth.MeteringPoint meteringpoint:
        :param datetime.datetime begin:
        :rtype: BIP32Key
        """
        return KeyGenerator \
            .get_key_for_metering_point(meteringpoint) \
            .ChildKey(minutes_since_epoch(begin))

    @staticmethod
    def get_key_for_traded_ggo_at_index(user, index):
        """
        :param origin.auth.User user:
        :param int index:
        :rtype: BIP32Key
        """
        return KeyGenerator \
            .get_key_for_user(user) \
            .ChildKey(0) \
            .ChildKey(index)

    @staticmethod
    def get_key_for_traded_ggo(ggo):
        """
        :param origin.ggo.Ggo ggo:
        :rtype: BIP32Key
        """
        assert ggo.issued is False
        assert ggo.key_index is not None

        return KeyGenerator \
            .get_key_for_traded_ggo_at_index(ggo.user, ggo.key_index)

    @staticmethod
    def get_key_for_issued_ggo(ggo):
        """
        :param origin.ggo.Ggo ggo:
        :rtype: BIP32Key
        """
        assert ggo.issued is True
        assert ggo.issue_meteringpoint is not None

        return KeyGenerator \
            .get_key_for_metering_point(ggo.issue_meteringpoint) \
            .ChildKey(minutes_since_epoch(ggo.begin))

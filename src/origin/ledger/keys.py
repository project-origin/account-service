from bip32utils import BIP32Key


class KeyGenerator(object):
    """
    TODO
    """

    @staticmethod
    def get_key_for_user(user):
        """
        :param User user:
        :rtype: BIP32Key
        """
        return BIP32Key.fromExtendedKey(user.master_extended_key)

    @staticmethod
    def set_key_for_user(user, key):
        """
        :param User user:
        :param BIP32Key key:
        """
        user.master_extended_key = key.ExtendedKey()

    @staticmethod
    def set_key_for_user_from_entropy(user, entropy):
        """
        :param User user:
        :param str entropy:
        """
        KeyGenerator.set_key_for_user(
            user, BIP32Key.fromEntropy(entropy.encode()))

    @staticmethod
    def get_key_for_metering_point(meteringpoint):
        """
        :param MeteringPoint meteringpoint:
        :rtype: BIP32Key
        """
        return KeyGenerator \
            .get_key_for_user(meteringpoint.user) \
            .ChildKey(1) \
            .ChildKey(meteringpoint.key_index)

    @staticmethod
    def get_key_for_measurement(meteringpoint, begin):
        """
        :param MeteringPoint meteringpoint:
        :param datetime.datetime begin:
        :rtype: BIP32Key
        """
        # Begin in minutes since epoch
        m = int(begin.replace(second=0, microsecond=0).timestamp())

        return KeyGenerator \
            .get_key_for_metering_point(meteringpoint) \
            .ChildKey(m)

    @staticmethod
    def get_key_for_traded_ggo_at_index(user, index):
        """
        :param User user:
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
        :param Ggo ggo:
        :rtype: BIP32Key
        """
        assert ggo.issued is False
        assert ggo.key_index is not None

        return KeyGenerator \
            .get_key_for_traded_ggo_at_index(ggo.user, ggo.key_index)

    @staticmethod
    def get_key_for_issued_ggo(ggo):
        """
        :param Ggo ggo:
        :rtype: BIP32Key
        """
        assert ggo.issued is True
        assert ggo.issue_meteringpoint is not None

        # Begin in minutes since epoch
        m = int(ggo.begin.replace(second=0, microsecond=0).timestamp())

        return KeyGenerator \
            .get_key_for_metering_point(ggo.issue_meteringpoint) \
            .ChildKey(m)

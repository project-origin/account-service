import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from origin.ggo.composer import GgoComposer
from origin.ledger import SplitTransaction, RetireTransaction


# -- Constructor -------------------------------------------------------------


def test__GgoComposer__ggo_is_not_tradable__should_raise_AssertionError():
    ggo = Mock()
    ggo.is_tradable.return_value = False
    ggo.is_expired.return_value = False

    with pytest.raises(AssertionError):
        GgoComposer(ggo=ggo, session=Mock())


def test__GgoComposer__ggo_is_expired__should_raise_AssertionError():
    ggo = Mock()
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = True

    with pytest.raises(AssertionError):
        GgoComposer(ggo=ggo, session=Mock())


# -- add_retire() ------------------------------------------------------------


def test__GgoComposer__add_retire__meteringpoint_different_user__should_raise_AssertionError():
    """
    There does not exists any [consumption] Measurement for the
    provided GSRN at the GGOs "begin"
    """

    # Arrange
    ggo = Mock(amount=100, begin=datetime(2020, 1, 1, 0, 0, 0), user_id=1)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False

    composer = GgoComposer(ggo=ggo, session=Mock())

    # Act + Assert
    with pytest.raises(AssertionError):
        composer.add_retire(meteringpoint=Mock(user_id=2), amount=100)


@patch('origin.ggo.composer.datahub_service')
def test__GgoComposer__add_retire__no_measurement_available__should_raise_RetireMeasurementUnavailable(datahub):
    """
    There does not exists any [consumption] Measurement for the
    provided GSRN at the GGOs "begin"
    """

    # Arrange
    ggo = Mock(amount=100, begin=datetime(2020, 1, 1, 0, 0, 0), user_id=1)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False

    datahub.get_consumption.return_value = Mock(measurement=None)
    composer = GgoComposer(ggo=ggo, session=Mock())

    # Act + Assert
    with pytest.raises(composer.RetireMeasurementUnavailable):
        composer.add_retire(meteringpoint=Mock(user_id=1), amount=100)


@patch('origin.ggo.composer.datahub_service')
def test__GgoComposer__add_retire__measurement_and_ggo_different_sector__should_raise_RetireMeasurementInvalid(datahub):
    """
    GGO can only be retired to Measurements within the same "sector"
    """

    # Arrange
    ggo = Mock(amount=100, begin=datetime(2020, 1, 1, 0, 0, 0), sector='DK1', user_id=1)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False

    measurement = Mock(sector='DK2', begin=datetime(2020, 1, 1, 0, 0, 0))

    datahub.get_consumption.return_value = Mock(measurement=measurement)
    composer = GgoComposer(ggo=ggo, session=Mock())

    # Act + Assert
    with pytest.raises(composer.RetireMeasurementInvalid):
        composer.add_retire(meteringpoint=Mock(user_id=1), amount=100)


@patch('origin.ggo.composer.datahub_service')
def test__GgoComposer__add_retire__measurement_and_ggo_different_begin__should_raise_RetireMeasurementInvalid(datahub):
    """
    GGO can only be retired to Measurements at the same "begin"
    """

    # Arrange
    ggo = Mock(amount=100, begin=datetime(2020, 1, 1, 0, 0, 0), sector='DK1', user_id=1)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False

    measurement = Mock(sector='DK1', begin=datetime(2021, 1, 1, 0, 0, 0))

    datahub.get_consumption.return_value = Mock(measurement=measurement)
    composer = GgoComposer(ggo=ggo, session=Mock())

    # Act + Assert
    with pytest.raises(composer.RetireMeasurementInvalid):
        composer.add_retire(meteringpoint=Mock(user_id=1), amount=100)


@patch('origin.ggo.composer.datahub_service')
@pytest.mark.parametrize('retire_amount', (-1, 0, 101))
def test__GgoComposer__add_retire__invalid_amount__should_raise_AssertionError(datahub, retire_amount):
    """
    The amount to retire should be > 0 and <= ggo.amount
    """

    # Arrange
    ggo = Mock(amount=100, begin=datetime(2020, 1, 1, 0, 0, 0), user_id=1)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False

    datahub.get_consumption.return_value = Mock(measurement=None)
    composer = GgoComposer(ggo=ggo, session=Mock())

    # Act + Assert
    with pytest.raises(AssertionError):
        composer.add_retire(meteringpoint=Mock(user_id=1), amount=retire_amount)


@patch('origin.ggo.composer.datahub_service')
@pytest.mark.parametrize(
    'measured, retired, requested, actual', (
    (200,      0,       100,       100),
    (200,      50,      100,       100),
    (50,       0,       100,       50),
    (200,      200,     100,       None),
    (50,       100,     100,       None),
    (0,        0,       100,       None),
))
def test__GgoComposer__add_retire__should_retire_actual_amount(
        datahub, measured, retired, requested, actual):
    """
    The actual amount to retire should not exceed
    """

    # Arrange
    sector = 'DK1'
    begin = datetime(2020, 1, 1, 0, 0, 0)

    ggo = Mock(amount=100, begin=begin, sector=sector, user_id=1)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False

    measurement = Mock(sector=sector, begin=begin, amount=measured)

    datahub.get_consumption.return_value = Mock(measurement=measurement)

    composer = GgoComposer(ggo=ggo, session=Mock())
    composer.get_retired_amount = Mock()
    composer.get_retired_amount.return_value = retired

    # Act
    composer.add_retire(meteringpoint=Mock(user_id=1), amount=requested)

    # Assert
    if actual is None:
        # Expect nothing to be retired
        assert len(composer.retires) == 0
    else:
        assert composer.retires[0][2] == actual


# -- build_batch() -----------------------------------------------------------


def test__GgoComposer__build_batch__nothing_added__should_raise_Empty():

    # Arrange
    ggo = Mock()
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False

    composer = GgoComposer(ggo=ggo, session=Mock())

    # Act + Assert
    with pytest.raises(composer.Empty):
        composer.build_batch()


@patch('origin.ggo.composer.datahub_service')
@pytest.mark.parametrize(
    'transfer_amounts,      retire_amounts', (
    ((40, 40),              (40, 40)),
    ((40, 40, 40),          ()),
    ((),                    (40, 40, 40)),
))
def test__GgoComposer__build_batch__total_amount_exceeds_available_amount__should_raise_AmountUnavailable(
        datahub, transfer_amounts, retire_amounts):

    #  -- Arrange ------------------------------------------------------------

    sector = 'DK1'
    begin = datetime(2020, 1, 1, 0, 0, 0)

    ggo = Mock(amount=100, begin=begin, sector=sector, user_id=1)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False

    datahub.get_consumption.return_value = Mock(measurement=Mock(
        sector=sector,
        begin=begin,
        amount=100,
    ))

    composer = GgoComposer(ggo=ggo, session=Mock())
    composer.get_retired_amount = Mock()
    composer.get_retired_amount.return_value = 0

    #  -- Act + Assert -------------------------------------------------------

    for transfer_amount in transfer_amounts:
        composer.add_transfer(user=Mock(), amount=transfer_amount)
    for retire_amount in retire_amounts:
        composer.add_retire(meteringpoint=Mock(user_id=1), amount=retire_amount)

    with pytest.raises(composer.AmountUnavailable):
        composer.build_batch()


@patch('origin.ggo.composer.datahub_service')
@pytest.mark.parametrize(
    'transfer_amounts,      remaining_amount', (
    ((100,),                0),
    ((50, 50),              0),
    ((40,),                 60),
))
def test__GgoComposer__build_batch__only_transfer__should_build_batch_and_add_remaining_to_current_owner(
        datahub, transfer_amounts, remaining_amount):
    """
    :param list[int] transfer_amounts:
    :param int remaining_amount:
    """

    #  -- Arrange ------------------------------------------------------------

    sector = 'DK1'
    begin = datetime(2020, 1, 1, 0, 0, 0)

    ggo = Mock(amount=100, begin=begin, sector=sector, stored=True, retired=False, locked=False, synchronized=True)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False
    ggo.create_child.side_effect = lambda amount, user: Mock(amount=amount, user=user)

    datahub.get_consumption.return_value = Mock(measurement=Mock(
        sector=sector,
        begin=begin,
        amount=100,
    ))

    composer = GgoComposer(ggo=ggo, session=Mock())
    composer.get_retired_amount = Mock()
    composer.get_retired_amount.return_value = 0

    transfer_users = [Mock(name=f'User {i}') for i in range(len(transfer_amounts))]

    #  -- Act ----------------------------------------------------------------

    for user, amount in zip(transfer_users, transfer_amounts):
        composer.add_transfer(user, amount)

    batch, recipients = composer.build_batch()

    #  -- Assert -------------------------------------------------------------

    assert len(batch.transactions) == 1
    assert type(batch.transactions[0]) is SplitTransaction

    if remaining_amount > 0:
        assert len(recipients) == len(transfer_amounts) + 1
    else:
        assert len(recipients) == len(transfer_amounts)

    recipients_dict = dict(recipients)  # {User: Ggo}

    for i, (user, amount) in enumerate(zip(transfer_users, transfer_amounts)):
        assert user in recipients_dict
        assert recipients_dict[user].amount == amount
        assert batch.transactions[0].parent_ggo is ggo
        assert batch.transactions[0].targets[i].ggo.user is user
        assert batch.transactions[0].targets[i].ggo.amount == amount


@patch('origin.ggo.composer.datahub_service')
def test__GgoComposer__build_batch__retire_full_amount_to_one_gsrn__should_build_batch_with_one_RetireTransaction(datahub):

    #  -- Arrange ------------------------------------------------------------

    sector = 'DK1'
    begin = datetime(2020, 1, 1, 0, 0, 0)

    ggo = Mock(amount=100, begin=begin, sector=sector, stored=True, retired=False, locked=False, synchronized=True, user_id=1)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False
    ggo.create_child.side_effect = lambda amount, user: Mock(amount=amount, user=user)

    meteringpoint = Mock(gsrn='GSRN1', user_id=1)
    measurement = Mock(sector=sector, begin=begin, amount=100, address='MEASUREMENT-ADDRESS')

    datahub.get_consumption.return_value = Mock(measurement=measurement)

    composer = GgoComposer(ggo=ggo, session=Mock())
    composer.get_retired_amount = Mock()
    composer.get_retired_amount.return_value = 0

    #  -- Act ----------------------------------------------------------------

    composer.add_retire(meteringpoint=meteringpoint, amount=100)
    batch, recipients = composer.build_batch()

    #  -- Assert -------------------------------------------------------------

    assert len(recipients) == 0
    assert len(batch.transactions) == 1
    assert type(batch.transactions[0]) is RetireTransaction
    assert batch.transactions[0].parent_ggo is ggo
    assert batch.transactions[0].parent_ggo.retire_gsrn == 'GSRN1'
    assert batch.transactions[0].parent_ggo.retire_address == 'MEASUREMENT-ADDRESS'
    assert batch.transactions[0].meteringpoint is meteringpoint
    assert batch.transactions[0].measurement_address == 'MEASUREMENT-ADDRESS'


@patch('origin.ggo.composer.datahub_service')
def test__GgoComposer__build_batch__multiple_retires__should_build_batch_with_one_SplitTransaction_and_multiple_RetireTransactions(datahub):

    #  -- Arrange ------------------------------------------------------------

    sector = 'DK1'
    begin = datetime(2020, 1, 1, 0, 0, 0)

    ggo = Mock(amount=100, begin=begin, sector=sector, stored=True, retired=False, locked=False, synchronized=True, user_id=1)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False
    ggo.create_child.side_effect = lambda amount, user: Mock(amount=amount, user=user, begin=begin)

    meteringpoint1 = Mock(gsrn='GSRN1', user_id=1)
    meteringpoint2 = Mock(gsrn='GSRN2', user_id=1)
    measurement = Mock(sector=sector, begin=begin, amount=100, address='MEASUREMENT-ADDRESS')

    datahub.get_consumption.return_value = Mock(measurement=measurement)

    composer = GgoComposer(ggo=ggo, session=Mock())
    composer.get_retired_amount = Mock()
    composer.get_retired_amount.return_value = 0

    #  -- Act ----------------------------------------------------------------

    composer.add_retire(meteringpoint=meteringpoint1, amount=80)
    composer.add_retire(meteringpoint=meteringpoint2, amount=20)
    batch, recipients = composer.build_batch()

    #  -- Assert -------------------------------------------------------------

    assert len(recipients) == 0
    assert len(batch.transactions) == 3

    split = batch.transactions[0]
    retire1 = batch.transactions[1]
    retire2 = batch.transactions[2]

    # SplitTransaction
    assert type(split) is SplitTransaction
    assert len(split.targets) == 2

    # RetireTransaction 1
    assert type(retire1) is RetireTransaction
    assert retire1.begin == begin
    assert retire1.parent_ggo is split.targets[0].ggo
    assert retire1.parent_ggo.retire_gsrn == 'GSRN1'
    assert retire1.parent_ggo.retire_address == 'MEASUREMENT-ADDRESS'
    assert retire1.parent_ggo.amount == 80
    assert retire1.meteringpoint is meteringpoint1
    assert retire1.measurement_address == 'MEASUREMENT-ADDRESS'

    # RetireTransaction 2
    assert type(retire2) is RetireTransaction
    assert retire2.begin == begin
    assert retire2.parent_ggo is split.targets[1].ggo
    assert retire2.parent_ggo.retire_gsrn == 'GSRN2'
    assert retire2.parent_ggo.retire_address == 'MEASUREMENT-ADDRESS'
    assert retire2.parent_ggo.amount == 20
    assert retire2.meteringpoint is meteringpoint2
    assert retire2.measurement_address == 'MEASUREMENT-ADDRESS'


@patch('origin.ggo.composer.datahub_service')
def test__GgoComposer__build_batch__multiple_retires_and_transfers__should_build_batch_with_one_SplitTransaction_and_multiple_RetireTransactions(datahub):

    #  -- Arrange ------------------------------------------------------------

    sector = 'DK1'
    begin = datetime(2020, 1, 1, 0, 0, 0)

    ggo = Mock(amount=100, begin=begin, sector=sector, stored=True, retired=False, locked=False, synchronized=True, user_id=1)
    ggo.is_tradable.return_value = True
    ggo.is_expired.return_value = False
    ggo.create_child.side_effect = lambda amount, user: Mock(amount=amount, user=user, begin=begin)

    user1 = Mock()
    user2 = Mock()

    meteringpoint1 = Mock(gsrn='GSRN1', user_id=1)
    meteringpoint2 = Mock(gsrn='GSRN2', user_id=1)
    measurement = Mock(sector=sector, begin=begin, amount=100, address='MEASUREMENT-ADDRESS')

    datahub.get_consumption.return_value = Mock(measurement=measurement)

    composer = GgoComposer(ggo=ggo, session=Mock())
    composer.get_retired_amount = Mock()
    composer.get_retired_amount.return_value = 0

    #  -- Act ----------------------------------------------------------------

    composer.add_transfer(user=user1, amount=15, reference='REF1')
    composer.add_transfer(user=user2, amount=30, reference='REF2')
    composer.add_retire(meteringpoint=meteringpoint1, amount=10)
    composer.add_retire(meteringpoint=meteringpoint2, amount=40)

    # Sum of transfers + retires = 95 (5 remaining)

    batch, recipients = composer.build_batch()

    #  -- Assert -------------------------------------------------------------

    assert len(recipients) == 3
    assert len(batch.transactions) == 3

    split = batch.transactions[0]
    retire1 = batch.transactions[1]
    retire2 = batch.transactions[2]

    # SplitTransaction
    assert type(split) is SplitTransaction
    assert len(split.targets) == 5
    assert split.parent_ggo is ggo
    assert split.targets[0].ggo.user is user1
    assert split.targets[0].ggo.amount == 15
    assert split.targets[0].reference == 'REF1'
    assert split.targets[1].ggo.user is user2
    assert split.targets[1].ggo.amount == 30
    assert split.targets[1].reference == 'REF2'
    assert split.targets[2].ggo.user is ggo.user
    assert split.targets[2].ggo.amount == 5
    assert split.targets[2].reference is None

    # RetireTransaction 1
    assert type(retire1) is RetireTransaction
    assert retire1.begin == begin
    assert retire1.parent_ggo is split.targets[3].ggo
    assert retire1.parent_ggo.retire_gsrn == 'GSRN1'
    assert retire1.parent_ggo.retire_address == 'MEASUREMENT-ADDRESS'
    assert retire1.parent_ggo.amount == 10
    assert retire1.meteringpoint is meteringpoint1
    assert retire1.measurement_address == 'MEASUREMENT-ADDRESS'

    # RetireTransaction 2
    assert type(retire2) is RetireTransaction
    assert retire2.begin == begin
    assert retire2.parent_ggo is split.targets[4].ggo
    assert retire2.parent_ggo.retire_gsrn == 'GSRN2'
    assert retire2.parent_ggo.retire_address == 'MEASUREMENT-ADDRESS'
    assert retire2.parent_ggo.amount == 40
    assert retire2.meteringpoint is meteringpoint2
    assert retire2.measurement_address == 'MEASUREMENT-ADDRESS'

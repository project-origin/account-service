from origin.db import make_session
from origin.ggo import Ggo


session = make_session()
session.add(Ggo(
    user_id=3,
    address='123',

))

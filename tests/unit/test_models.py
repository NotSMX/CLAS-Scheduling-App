import pytest
from werkzeug.security import check_password_hash
from website.models import User

def test_set_hashed_password():
    user = User()
    password = "mysecretpassword"

    user.set_password(password)

    assert user.password_hash is not None
    assert user.password_hash != password
    assert check_password_hash(user.password_hash, password)

def test_check_password():
    user = User()
    password = "mypassword"
    user.set_password(password)

    assert user.check_password(password) is True

def test_check_incorrect_password():
    user = User()
    password = "mypassword"
    user.set_password(password)

    assert user.check_password("wrongpassword") is False

def test_check_unhashed_password():
    user = User()
    assert user.check_password("something") is False
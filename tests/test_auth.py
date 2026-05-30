def test_create_and_login(auth_db):
    import pykms_auth as auth

    auth.create_admin('adminuser', 'longpassword123')
    user = auth.verify_login('adminuser', 'longpassword123')
    assert user is not None
    assert user['username'] == 'adminuser'


def test_wrong_password(auth_db):
    import pykms_auth as auth

    auth.create_admin('adminuser', 'longpassword123')
    assert auth.verify_login('adminuser', 'wrongpassword12') is None


def test_change_password(auth_db):
    import pykms_auth as auth

    auth.create_admin('adminuser', 'longpassword123')
    user = auth.verify_login('adminuser', 'longpassword123')
    auth.change_password(user['id'], 'longpassword123', 'newpassword1234')
    assert auth.verify_login('adminuser', 'newpassword1234')

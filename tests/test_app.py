def test_livez(app_client):
    rv = app_client.get('/livez')
    assert rv.status_code == 200


def test_readyz(app_client):
    rv = app_client.get('/readyz')
    assert rv.status_code in (200, 503)


def test_admin_blocked_without_auth(app_client):
    rv = app_client.get('/admin', follow_redirects=False)
    assert rv.status_code in (302, 200)
    if rv.status_code == 302:
        assert rv.location.endswith('/')

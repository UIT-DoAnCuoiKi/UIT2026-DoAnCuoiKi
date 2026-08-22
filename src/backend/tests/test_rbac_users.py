def _token(client, username, password):
    return client.post("/auth/login", json={"username": username, "password": password}).json()["access_token"]


def test_no_token_rejected(client):
    assert client.get("/users").status_code in (401, 403)


def test_staff_cannot_access_users(client, make_user):
    make_user(username="staff1", password="pw", role="staff")
    token = _token(client, "staff1", "pw")
    r = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_admin_crud_and_lock(client, make_user):
    make_user(username="admin1", password="pw", role="admin")
    h = {"Authorization": f"Bearer {_token(client, 'admin1', 'pw')}"}

    r = client.post("/users", json={"username": "newstaff", "password": "pw2", "role": "staff"}, headers=h)
    assert r.status_code == 201
    new_id = r.json()["id"]

    r = client.get("/users", headers=h)
    assert len(r.json()) == 2

    assert client.post("/auth/login", json={"username": "newstaff", "password": "pw2"}).status_code == 200

    r = client.patch(f"/users/{new_id}", json={"active": False}, headers=h)
    assert r.status_code == 200 and r.json()["active"] is False

    assert client.post("/auth/login", json={"username": "newstaff", "password": "pw2"}).status_code == 401

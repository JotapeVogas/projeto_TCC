def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "UP"
    assert payload["database"] == "OK"


def test_crud_flow_usuarios(client):
    create_payload = {
        "nome": "Joao Test",
        "ativo": 1,
    }

    create_response = client.post("/usuarios", json=create_payload)
    assert create_response.status_code == 201

    created_user = create_response.json()
    assert created_user["id"] is not None
    user_id = created_user["id"]

    list_response = client.get("/usuarios")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert "lista" in list_payload
    assert len(list_payload["lista"]) == 1
    assert list_payload["lista"][0]["id"] == user_id

    update_payload = {
        "id": user_id,
        "nome": "Joao Updated",
        "ativo": 1,
    }
    update_response = client.patch("/usuarios", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["nome"] == "Joao Updated"

    deactivate_response = client.delete(f"/usuarios/{user_id}")
    assert deactivate_response.status_code == 204

    inactive_response = client.get(f"/usuarios?id={user_id}&ativo=0")
    assert inactive_response.status_code == 200
    inactive_payload = inactive_response.json()
    assert len(inactive_payload["lista"]) == 1
    assert inactive_payload["lista"][0]["ativo"] == 0

    activate_response = client.patch(f"/usuarios/{user_id}")
    assert activate_response.status_code == 200
    activate_payload = activate_response.json()
    assert activate_payload["status"] == "ativo"

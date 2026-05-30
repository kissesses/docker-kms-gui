import json


def test_protocol_overview():
    import pykms_protocol as protocol

    overview = protocol.build_protocol_overview()
    assert overview['transport']['port'] == 1688
    assert len(overview['client_request_fields']) >= 5
    assert len(overview['server_response_fields']) >= 4
    assert len(overview['flow_steps']) == 5


def test_client_session():
    import pykms_protocol as protocol

    client = {
        'clientMachineId': 'abc-123',
        'machineName': 'PC-01',
        'applicationId': 'Windows',
        'skuId': 'Win11 Pro',
        'licenseStatus': 'Activated',
        'lastRequestTime': 1710000000,
        'kmsEpid': '01234-56789-ABCDE-12345-67890-12345-67890-123',
        'requestCount': 3,
        'machineIp': '10.0.0.5',
    }
    session = protocol.build_client_session(client)
    assert session['binding']['machine_name'] == 'PC-01'
    assert session['received_from_client']['clientMachineId'] == 'abc-123'
    assert session['sent_to_client']['vLRenewalInterval'] >= 15
    assert 'health' in session['schedule']

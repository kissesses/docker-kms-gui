#!/usr/bin/env python3
"""Create demo kms.db, kms-policy.json and optional data for release screenshots."""

import json
import os
import sqlite3
import sys
import time


def seed_policy(var_dir: str) -> None:
    policy = {
        "client_count": 26,
        "activation_interval_minutes": 120,
        "renewal_interval_minutes": 10080,
        "hwid": "RANDOM",
        "port": 1688,
        "host": "kms",
        "licensing_validity_days": 180,
        "updated_at": int(time.time()),
    }
    path = os.path.join(var_dir, "kms-policy.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(policy, f, indent=2)
        f.write("\n")


def seed(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    now = int(time.time())

    clients = [
        (
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "DESKTOP-WIN11-PRO",
            "Windows",
            "48a2b1c3-d4e5-f678-9012-3456789abcde",
            "Activated",
            now - 3600,
            "01234-56789-02345-67890-01234-56789-23456",
            128,
            "192.168.1.42",
        ),
        (
            "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "OFFICE-PC-01",
            "Office",
            "98d8b1a2-c3d4-e567-8901-234567890abc",
            "Activated",
            now - 7200,
            "01234-56789-02345-67890-01234-56789-34567",
            64,
            "192.168.1.15",
        ),
        (
            "c3d4e5f6-a7b8-9012-cdef-123456789012",
            "LAPTOP-DEV",
            "Windows",
            "48a2b1c3-d4e5-f678-9012-3456789abcde",
            "Notifications Mode",
            now - 900,
            "01234-56789-02345-67890-01234-56789-45678",
            12,
            "10.0.0.88",
        ),
        (
            "d4e5f6a7-b8c9-0123-def0-234567890123",
            "WS-2022-SRV",
            "Windows",
            "55c92633-dc06-497a-b984-953b8486d392",
            "Activated",
            now - 86400,
            "01234-56789-02345-67890-01234-56789-56789",
            256,
            "172.16.0.10",
        ),
    ]

    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "CREATE TABLE clients("
            "clientMachineId TEXT, machineName TEXT, applicationId TEXT, "
            "skuId TEXT, licenseStatus TEXT, lastRequestTime INTEGER, "
            "kmsEpid TEXT, requestCount INTEGER, "
            "PRIMARY KEY(clientMachineId, applicationId))"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)"
        )
        cur.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', '1')"
        )
        cur.execute("ALTER TABLE clients ADD COLUMN lastRequestIP TEXT")

        cur.executemany(
            "INSERT INTO clients VALUES (?,?,?,?,?,?,?,?,?)",
            clients,
        )


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/kms-screenshot/kms.db"
    var_dir = os.path.dirname(path) or "."
    seed(path)
    seed_policy(var_dir)
    print(f"Demo database written to {path}")
    print(f"KMS policy written to {os.path.join(var_dir, 'kms-policy.json')}")

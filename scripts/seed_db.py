"""
Seed Database Script
Carga datos de prueba en MongoDB para demo/testing
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorClient

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import settings


async def seed_database():
    """
    Carga datos de prueba en la base de datos
    """
    print("🌱 Seeding database...")
    
    # Conectar a MongoDB
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.database_name]
    
    try:
        # ==========================================
        # 1. USERS
        # ==========================================
        print("\n👥 Creando usuarios...")
        
        users = [
            {
                "user_id": "user_1",
                "username": "alice_dev",
                "email": "alice@example.com",
                "full_name": "Alice Developer",
                "created_at": datetime.utcnow(),
                "is_active": True
            },
            {
                "user_id": "user_2",
                "username": "bob_sec",
                "email": "bob@example.com",
                "full_name": "Bob Security",
                "created_at": datetime.utcnow(),
                "is_active": True
            },
            {
                "user_id": "user_3",
                "username": "charlie_ops",
                "email": "charlie@example.com",
                "full_name": "Charlie DevOps",
                "created_at": datetime.utcnow(),
                "is_active": True
            }
        ]
        
        result = await db.users.insert_many(users)
        print(f"✅ Creados {len(result.inserted_ids)} usuarios")
        
        # ==========================================
        # 2. ALERTS
        # ==========================================
        print("\n🚨 Creando alertas...")
        
        now = datetime.utcnow()
        
        alerts = [
            {
                "alert_id": "alert_1",
                "signature": "dependabot_django_cve-2023-1234",
                "source_id": "dependabot",
                "severity": "CRITICAL",
                "component": "django@2.2.0",
                "status": "open",
                "first_seen": now - timedelta(days=3),
                "last_seen": now - timedelta(days=3),
                "quality": "high",
                "normalized_payload": {
                    "cve_id": "CVE-2023-1234",
                    "description": "SQL Injection vulnerability in Django",
                    "affected_versions": ["<2.2.28"],
                    "fixed_version": "2.2.28"
                },
                "lifecycle_history": [
                    {
                        "status": "open",
                        "timestamp": now - timedelta(days=3),
                        "triggered_by": "system"
                    }
                ],
                "reopen_count": 0,
                "version": 1
            },
            {
                "alert_id": "alert_2",
                "signature": "trivy_express_cve-2023-5678",
                "source_id": "trivy",
                "severity": "HIGH",
                "component": "express@4.17.1",
                "status": "open",
                "first_seen": now - timedelta(days=2),
                "last_seen": now - timedelta(days=2),
                "quality": "high",
                "normalized_payload": {
                    "cve_id": "CVE-2023-5678",
                    "description": "Path traversal in Express.js",
                    "affected_versions": ["<4.18.0"],
                    "fixed_version": "4.18.0"
                },
                "lifecycle_history": [
                    {
                        "status": "open",
                        "timestamp": now - timedelta(days=2),
                        "triggered_by": "system"
                    }
                ],
                "reopen_count": 0,
                "version": 1
            },
            {
                "alert_id": "alert_3",
                "signature": "zap_xss_homepage",
                "source_id": "zap",
                "severity": "MEDIUM",
                "component": "homepage.html",
                "status": "verified_resolved",
                "first_seen": now - timedelta(days=5),
                "last_seen": now - timedelta(days=5),
                "quality": "medium",
                "normalized_payload": {
                    "vulnerability_type": "XSS",
                    "description": "Reflected XSS in search parameter",
                    "location": "/search?q=",
                    "confidence": "medium"
                },
                "lifecycle_history": [
                    {
                        "status": "open",
                        "timestamp": now - timedelta(days=5),
                        "triggered_by": "system"
                    },
                    {
                        "status": "pending_verification",
                        "timestamp": now - timedelta(days=4),
                        "triggered_by": "user_1"
                    },
                    {
                        "status": "verified_resolved",
                        "timestamp": now - timedelta(days=4, hours=2),
                        "triggered_by": "system"
                    }
                ],
                "reopen_count": 0,
                "version": 1
            }
        ]
        
        result = await db.alerts.insert_many(alerts)
        print(f"✅ Creadas {len(result.inserted_ids)} alertas")
        
        # ==========================================
        # 3. REMEDIATIONS
        # ==========================================
        print("\n🔧 Creando remediaciones...")
        
        remediations = [
            {
                "remediation_id": "rem_1",
                "alert_id": "alert_3",
                "user_id": "user_1",
                "status": "verified",
                "created_at": now - timedelta(days=4),
                "resolved_at": now - timedelta(days=4),
                "verified_at": now - timedelta(days=4, hours=2),
                "description": "Implemented input sanitization",
                "evidence_refs": ["commit_abc123"]
            }
        ]
        
        result = await db.remediations.insert_many(remediations)
        print(f"✅ Creadas {len(result.inserted_ids)} remediaciones")
        
        # ==========================================
        # 4. POINT TRANSACTIONS
        # ==========================================
        print("\n💰 Creando transacciones de puntos...")
        
        point_transactions = [
            {
                "txn_id": "txn_1",
                "user_id": "user_1",
                "points": 50,
                "rule_id": "PTS-001",
                "reason": "Remediación verificada: alert_3",
                "timestamp": now - timedelta(days=4, hours=2),
                "evidence_refs": {
                    "alert_id": "alert_3",
                    "remediation_id": "rem_1"
                },
                "metadata": {
                    "severity": "MEDIUM",
                    "speed_bonus": False
                }
            },
            {
                "txn_id": "txn_2",
                "user_id": "user_2",
                "points": 100,
                "rule_id": "PTS-001",
                "reason": "Remediación verificada (ejemplo)",
                "timestamp": now - timedelta(days=3),
                "evidence_refs": {},
                "metadata": {
                    "severity": "HIGH",
                    "speed_bonus": False
                }
            },
            {
                "txn_id": "txn_3",
                "user_id": "user_3",
                "points": 75,
                "rule_id": "PTS-001",
                "reason": "Remediación verificada (ejemplo)",
                "timestamp": now - timedelta(days=2),
                "evidence_refs": {},
                "metadata": {
                    "severity": "MEDIUM",
                    "speed_bonus": True
                }
            }
        ]
        
        result = await db.point_transactions.insert_many(point_transactions)
        print(f"✅ Creadas {len(result.inserted_ids)} transacciones")
        
        # ==========================================
        # 5. RESCAN RESULTS
        # ==========================================
        print("\n🔍 Creando resultados de rescan...")
        
        rescan_results = [
            {
                "rescan_id": "rescan_1",
                "alert_id": "alert_3",
                "remediation_id": "rem_1",
                "executed_at": now - timedelta(days=4, hours=2),
                "present": False,
                "scan_output": "No vulnerability found",
                "status": "completed"
            }
        ]
        
        result = await db.rescan_results.insert_many(rescan_results)
        print(f"✅ Creados {len(result.inserted_ids)} resultados de rescan")
        
        # ==========================================
        # Summary
        # ==========================================
        print("\n" + "="*50)
        print("🎉 Database seeded successfully!")
        print("="*50)
        print("\n📊 Resumen:")
        print("  👥 Usuarios: 3")
        print("  🚨 Alertas: 3 (1 resuelta, 2 abiertas)")
        print("  🔧 Remediaciones: 1")
        print("  💰 Transacciones: 3")
        print("  🔍 Rescans: 1")
        print("\n🔗 Leaderboard:")
        print("  1. bob_sec: 100 pts")
        print("  2. charlie_ops: 75 pts")
        print("  3. alice_dev: 50 pts")
        print("\n✅ Puedes iniciar la API: make dev")
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
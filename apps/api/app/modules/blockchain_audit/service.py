"""Blockchain audit trail — SHA-256 hashing, Merkle tree, Polygon anchoring."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blockchain import BlockchainAnchor
from app.core.config import settings

logger = structlog.get_logger()


def _hash_data(data: dict[str, Any]) -> str:
    """SHA-256 hash of canonicalised JSON."""
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _build_merkle_root(hashes: list[bytes]) -> bytes:
    """Recursive Merkle tree construction."""
    if not hashes:
        return b"\x00" * 32
    if len(hashes) == 1:
        return hashes[0]
    if len(hashes) % 2 == 1:
        hashes.append(hashes[-1])  # Duplicate last if odd
    next_level: list[bytes] = []
    for i in range(0, len(hashes), 2):
        combined = hashlib.sha256(hashes[i] + hashes[i + 1]).digest()
        next_level.append(combined)
    return _build_merkle_root(next_level)


async def queue_anchor(
    db: AsyncSession,
    org_id: uuid.UUID,
    event_type: str,
    entity_type: str,
    entity_id: uuid.UUID,
    data: dict[str, Any],
) -> BlockchainAnchor:
    """Hash data and store as pending anchor."""
    data_hash = _hash_data({"org_id": str(org_id), "event_type": event_type,
                             "entity_id": str(entity_id), **data})
    anchor = BlockchainAnchor(
        org_id=org_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        data_hash=data_hash,
        status="pending",
    )
    db.add(anchor)
    await db.commit()
    await db.refresh(anchor)
    logger.info("blockchain.queued", event_type=event_type, entity_id=str(entity_id))
    return anchor


async def get_pending_anchors(db: AsyncSession) -> list[BlockchainAnchor]:
    result = await db.execute(
        select(BlockchainAnchor).where(
            BlockchainAnchor.status == "pending",
            BlockchainAnchor.is_deleted == False,
        ).limit(100)
    )
    return list(result.scalars().all())


async def batch_submit(db: AsyncSession) -> dict[str, Any]:
    """Group pending anchors into a Merkle tree and submit to Polygon."""
    pending = await get_pending_anchors(db)
    if not pending:
        return {"status": "no_pending", "count": 0}

    hashes = [bytes.fromhex(a.data_hash) for a in pending]
    merkle_root = _build_merkle_root(hashes)
    merkle_root_hex = merkle_root.hex()
    batch_id = uuid.uuid4()

    # Attempt on-chain submission if credentials available
    tx_hash: str | None = None
    block_number: int | None = None

    try:
        polygon_rpc = getattr(settings, "POLYGON_RPC_URL", None)
        private_key = getattr(settings, "POLYGON_PRIVATE_KEY", None)
        contract_address = getattr(settings, "POLYGON_ANCHOR_CONTRACT", None)

        if polygon_rpc and private_key and contract_address:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(polygon_rpc))
            account = w3.eth.account.from_key(private_key)
            nonce = w3.eth.get_transaction_count(account.address)
            tx = {
                "to": contract_address,
                "data": "0x" + merkle_root_hex,
                "gas": 50000,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce,
                "chainId": 137,  # Polygon mainnet
            }
            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash_bytes = w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=120)
            tx_hash = receipt.transactionHash.hex()
            block_number = receipt.blockNumber
            logger.info("blockchain.anchored", tx_hash=tx_hash, block=block_number, count=len(pending))
        else:
            logger.warning("blockchain.no_credentials", msg="Anchors stored locally only")
    except Exception as exc:
        logger.error("blockchain.submit_failed", error=str(exc))

    # Update all anchors in the batch
    now = datetime.utcnow()
    for anchor in pending:
        anchor.merkle_root = merkle_root_hex
        anchor.batch_id = batch_id
        anchor.anchored_at = now
        anchor.status = "anchored" if tx_hash else "pending"
        if tx_hash:
            anchor.tx_hash = tx_hash
            anchor.block_number = block_number

    await db.commit()
    return {"status": "ok", "batch_id": str(batch_id), "count": len(pending),
            "merkle_root": merkle_root_hex, "tx_hash": tx_hash}


async def verify_anchor(db: AsyncSession, entity_type: str, entity_id: uuid.UUID) -> dict[str, Any]:
    """Verify an entity's most recent anchor."""
    result = await db.execute(
        select(BlockchainAnchor)
        .where(BlockchainAnchor.entity_type == entity_type, BlockchainAnchor.entity_id == entity_id,
               BlockchainAnchor.is_deleted == False)
        .order_by(BlockchainAnchor.created_at.desc())
        .limit(1)
    )
    anchor = result.scalar_one_or_none()
    if not anchor:
        return {"verified": False, "reason": "No anchor found"}

    verified = anchor.status == "anchored" and anchor.tx_hash is not None
    explorer_url = f"https://polygonscan.com/tx/{anchor.tx_hash}" if anchor.tx_hash else None

    return {
        "verified": verified,
        "anchor_id": str(anchor.id),
        "data_hash": anchor.data_hash,
        "merkle_root": anchor.merkle_root,
        "chain": anchor.chain,
        "tx_hash": anchor.tx_hash,
        "block_number": anchor.block_number,
        "anchored_at": anchor.anchored_at.isoformat() if anchor.anchored_at else None,
        "explorer_url": explorer_url,
        "status": anchor.status,
    }


async def list_entity_anchors(db: AsyncSession, entity_type: str, entity_id: uuid.UUID) -> list[BlockchainAnchor]:
    result = await db.execute(
        select(BlockchainAnchor)
        .where(BlockchainAnchor.entity_type == entity_type, BlockchainAnchor.entity_id == entity_id,
               BlockchainAnchor.is_deleted == False)
        .order_by(BlockchainAnchor.created_at.desc())
    )
    return list(result.scalars().all())

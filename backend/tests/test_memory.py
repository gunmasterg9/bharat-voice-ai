"""
Bharat Voice AI — Tests for Persistent SQLite Memory & Privacy Rules (Day 4)

Tests SQLite persistence, CRUD operations, connection survival across process restarts,
explicit consent enforcement, sensitive credential scrubbing, and user deletion protocols.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from memory.database import Database
from memory.memory_service import MemoryService, sanitize_facts


@pytest.fixture
def temp_db():
    """Fixture providing a temporary SQLite database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_bharat_voice.db"
        db = Database(db_path)
        yield db


@pytest.fixture
def memory_service(temp_db):
    """Fixture providing MemoryService linked to temp_db."""
    return MemoryService(temp_db)


def test_create_and_retrieve_user(memory_service):
    """Test creating and retrieving a user profile."""
    user_id = "test_caller_101"
    user = memory_service.save_user(
        user_id=user_id,
        name="Ramesh",
        language_preference="Hindi",
        facts={"location": "Ahmedabad", "preferred_topic": "technology"},
    )

    assert user is not None
    assert user["user_id"] == user_id
    assert user["name"] == "Ramesh"
    assert user["language_preference"] == "Hindi"
    assert user["facts"]["location"] == "Ahmedabad"
    assert user["facts"]["preferred_topic"] == "technology"


def test_update_facts_and_language(memory_service):
    """Test updating user facts and language preference incrementally."""
    user_id = "test_caller_102"
    memory_service.save_user(user_id=user_id, name="Anita")

    # Update facts
    memory_service.update_user_facts(user_id, {"communication_style": "Hinglish"})
    user = memory_service.get_user(user_id)
    assert user["facts"]["communication_style"] == "Hinglish"

    # Update language preference
    memory_service.update_language_preference(user_id, "Gujarati")
    user = memory_service.get_user(user_id)
    assert user["language_preference"] == "Gujarati"


def test_update_last_interaction(memory_service):
    """Test updating last_interaction timestamp."""
    user_id = "test_caller_103"
    memory_service.save_user(user_id=user_id, name="Suresh")
    profile = memory_service.update_last_interaction(user_id)
    assert profile["last_interaction"] is not None


def test_delete_user(memory_service):
    """Test deleting user profile from database."""
    user_id = "test_caller_104"
    memory_service.save_user(user_id=user_id, name="Priya")
    assert memory_service.get_user(user_id) is not None

    deleted = memory_service.delete_user(user_id)
    assert deleted is True
    assert memory_service.get_user(user_id) is None


def test_persistence_across_connection_restarts(temp_db):
    """Test that SQLite data survives database connection restarts."""
    db_path = temp_db.db_path
    user_id = "test_caller_restart"

    # Session 1: Write user
    service_1 = MemoryService(temp_db)
    service_1.save_user(
        user_id=user_id,
        name="Vikram",
        language_preference="Hindi",
        facts={"city": "Delhi"},
    )

    # Re-instantiate database connection (simulating process restart)
    new_db = Database(db_path)
    service_2 = MemoryService(new_db)

    # Session 2: Read user
    retrieved = service_2.get_user(user_id)
    assert retrieved is not None
    assert retrieved["name"] == "Vikram"
    assert retrieved["language_preference"] == "Hindi"
    assert retrieved["facts"]["city"] == "Delhi"


def test_sensitive_data_filtering():
    """Test that sensitive credentials (passwords, OTPs, PINs, bank details, ID numbers, medical notes) are blocked."""
    unsafe_facts = {
        "preferred_topic": "AI",
        "user_password": "secret_password_123",
        "otp_code": "987654",
        "bank_account": "1234567890",
        "account_number": "99887766",
        "credit_card": "4111222233334444",
        "aadhaar": "1234-5678-9012",
        "voter_id": "ABC1234567",
        "medical_notes": "Detailed clinical diagnosis notes",
        "location": "Mumbai",
    }

    clean = sanitize_facts(unsafe_facts)
    assert "user_password" not in clean
    assert "otp_code" not in clean
    assert "bank_account" not in clean
    assert "account_number" not in clean
    assert "credit_card" not in clean
    assert "aadhaar" not in clean
    assert "voter_id" not in clean
    assert "medical_notes" not in clean
    assert clean["preferred_topic"] == "AI"
    assert clean["location"] == "Mumbai"


def test_domain_track_facts_storage(memory_service):
    """Test saving allowable facts across all 6 domain tracks."""
    user_id = "test_domain_tracks_caller"

    domain_facts = {
        "farm_field": {
            "crops_grown": ["wheat", "mustard"],
            "land_size_acres": 5,
            "district": "Kheda",
            "irrigation_type": "canal",
        },
        "health_access": {
            "age_band": "30-45",
            "ongoing_conditions": ["hypertension"],
            "last_triage_outcome": "routine checkup advised",
        },
        "learning_literacy": {
            "current_level": "intermediate",
            "topics_covered": ["subtraction", "phonics"],
            "mistakes_keep_making": "borrowing in multi-digit subtraction",
        },
        "local_commerce": {
            "past_orders": ["5kg atta", "1L oil"],
            "usual_quantities": "weekly household pack",
            "preferred_delivery_slot": "morning 9-11 AM",
        },
        "financial_services": {
            "schemes_checked": ["PM-Kisan", "PMJJBY"],
            "eligibility_answers": "small farmer landholder eligible",
        },
        "disaster_response": {
            "location": "Ward 4, Relief Camp B",
            "household_size": 4,
            "mobility_needs": "elderly wheelchair assistance required",
            "last_check_in": "2026-08-09T08:00:00Z",
        },
    }

    user = memory_service.save_user(
        user_id=user_id,
        name="Sunita",
        language_preference="Hindi",
        facts=domain_facts,
    )

    assert user is not None
    assert user["facts"]["farm_field"]["crops_grown"] == ["wheat", "mustard"]
    assert user["facts"]["health_access"]["age_band"] == "30-45"
    assert user["facts"]["learning_literacy"]["current_level"] == "intermediate"
    assert (
        user["facts"]["local_commerce"]["preferred_delivery_slot"] == "morning 9-11 AM"
    )
    assert (
        user["facts"]["financial_services"]["eligibility_answers"]
        == "small farmer landholder eligible"
    )
    assert user["facts"]["disaster_response"]["household_size"] == 4


@pytest.mark.asyncio
async def test_agent_memory_tools_consent_enforcement():
    """Test that save_caller_memory tool enforces user_consent=True."""
    from agent.voice_agent import BharatVoiceAgent

    test_uid = "fresh_test_tool_user"
    agent = BharatVoiceAgent(session_id="test_session", user_id=test_uid)
    agent.db_memory.delete_user(test_uid)  # Ensure clean slate

    # Attempt to save without consent
    res_no_consent = await agent.save_caller_memory(
        context=None,
        user_id=test_uid,
        name="Sunil",
        user_consent=False,
    )
    assert "blocked" in res_no_consent.lower()
    assert agent.db_memory.get_user(test_uid) is None

    # Save with explicit consent
    res_consent = await agent.save_caller_memory(
        context=None,
        user_id=test_uid,
        name="Sunil",
        language_preference="Hindi",
        facts='{"topic": "Cricket"}',
        user_consent=True,
    )
    assert "successfully saved" in res_consent.lower()

    profile = agent.db_memory.get_user(test_uid)
    assert profile is not None
    assert profile["name"] == "Sunil"
    assert profile["language_preference"] == "Hindi"

    # Cleanup
    agent.db_memory.delete_user(test_uid)


@pytest.mark.asyncio
async def test_agent_forget_caller_tool():
    """Test forget_caller tool with explicit user confirmation."""
    from agent.voice_agent import BharatVoiceAgent

    test_uid = "fresh_forget_user"
    agent = BharatVoiceAgent(session_id="test_session", user_id=test_uid)
    agent.db_memory.save_user(user_id=test_uid, name="Kiran")

    # Attempt deletion without confirmation
    res_no_confirm = await agent.forget_caller(
        context=None,
        user_id=test_uid,
        user_confirmation=False,
    )
    assert "blocked" in res_no_confirm.lower()
    assert agent.db_memory.get_user(test_uid) is not None

    # Delete with explicit confirmation
    res_confirm = await agent.forget_caller(
        context=None,
        user_id=test_uid,
        user_confirmation=True,
    )
    assert "removed" in res_confirm.lower()
    assert agent.db_memory.get_user(test_uid) is None


@pytest.mark.asyncio
async def test_rag_knowledge_base_retrieval():
    """Test RAG Knowledge Base search service and agent tool query_knowledge_base."""
    from agent.voice_agent import BharatVoiceAgent
    from services.knowledge_base import get_knowledge_base_service

    kb = get_knowledge_base_service()

    # Direct RAG search test for Cotton Pink Bollworm advisory
    results = kb.search("pink bollworm cotton spraying", track="Farm & Field")
    assert len(results) > 0
    assert "Cotton" in results[0]["title"]
    assert "Profenofos" in results[0]["grounded_content"]

    # RAG tool test via agent
    agent = BharatVoiceAgent(session_id="rag_test_session")
    tool_res = await agent.query_knowledge_base(
        context=None,
        query="PMJJBY 436 life insurance",
        track="Financial Services",
    )
    assert "PMJJBY" in tool_res
    assert "₹436" in tool_res

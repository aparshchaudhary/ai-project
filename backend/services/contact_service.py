"""
WhatsApp Contact Book & Recipient Resolution Service.
Handles:
- Storage & retrieval of contacts from SQLite DB
- Ambiguity detection (multiple contacts with same or similar names)
- Exact, alias, and fuzzy contact matching
- Contact creation and management
- Strict security: recipient verification before any message dispatch
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional, Tuple

from backend.database.database import SessionLocal
from backend.database.models import Contact

logger = logging.getLogger(__name__)

# Pre-seeded default contacts for testing and demonstration
DEFAULT_CONTACTS = [
    {"name": "Ram Sharma", "phone": "+919876543210", "relationship": "Colleague", "email": "ram.sharma@example.com"},
    {"name": "Ram Kumar", "phone": "+919876543211", "relationship": "Friend", "email": "ram.kumar@example.com"},
    {"name": "Rahul Verma", "phone": "+919811122233", "relationship": "Classmate", "email": "rahul.v@example.com"},
    {"name": "Mom", "phone": "+919899001122", "relationship": "Mother", "email": "mom@family.local"},
    {"name": "Dad", "phone": "+919899001133", "relationship": "Father", "email": "dad@family.local"},
    {"name": "Priya Singh", "phone": "+919765432199", "relationship": "Manager", "email": "priya.s@work.com"},
]


class ContactService:
    def __init__(self):
        self._seed_default_contacts()

    def _seed_default_contacts(self):
        """Ensures default contacts exist in SQLite database on startup."""
        db = SessionLocal()
        try:
            existing = {c.name.lower() for c in db.query(Contact.name).all()}
            for item in DEFAULT_CONTACTS:
                if item["name"].lower() not in existing:
                    contact = Contact(
                        name=item["name"],
                        phone=item["phone"],
                        relationship=item["relationship"],
                        email=item["email"]
                    )
                    db.add(contact)
            db.commit()
        except Exception as e:
            logger.error(f"Error seeding contacts: {e}")
            db.rollback()
        finally:
            db.close()

    def list_contacts(self) -> List[Dict[str, Any]]:
        """Returns all contacts."""
        db = SessionLocal()
        try:
            contacts = db.query(Contact).all()
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "phone": c.phone,
                    "relationship": c.relationship,
                    "email": c.email
                }
                for c in contacts
            ]
        finally:
            db.close()

    def add_contact(self, name: str, phone: str, relationship: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
        """Creates or updates a contact."""
        db = SessionLocal()
        try:
            existing = db.query(Contact).filter(Contact.name.ilike(name.strip())).first()
            if existing:
                existing.phone = phone.strip()
                if relationship:
                    existing.relationship = relationship
                if email:
                    existing.email = email
                contact_obj = existing
            else:
                contact_obj = Contact(
                    name=name.strip(),
                    phone=phone.strip(),
                    relationship=relationship,
                    email=email
                )
                db.add(contact_obj)
            db.commit()
            db.refresh(contact_obj)
            return {
                "id": contact_obj.id,
                "name": contact_obj.name,
                "phone": contact_obj.phone,
                "relationship": contact_obj.relationship,
                "email": contact_obj.email
            }
        finally:
            db.close()

    def resolve_contact(self, query: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Resolves a spoken name to a verified contact.
        Returns:
            (single_matched_contact, list_of_ambiguous_matches)
        
        - If exactly 1 match found: returns (contact, [contact])
        - If multiple matches found: returns (None, [match1, match2, ...])
        - If 0 matches found: returns (None, [])
        """
        if not query or not query.strip():
            return None, []

        clean = query.strip().lower()
        db = SessionLocal()
        try:
            all_contacts = db.query(Contact).all()

            # 1. Exact match (case-insensitive)
            exact = [c for c in all_contacts if c.name.lower() == clean]
            if len(exact) == 1:
                c = exact[0]
                return {
                    "id": c.id,
                    "name": c.name,
                    "phone": c.phone,
                    "relationship": c.relationship,
                    "email": c.email
                }, [{
                    "id": c.id,
                    "name": c.name,
                    "phone": c.phone,
                    "relationship": c.relationship,
                    "email": c.email
                }]

            # 2. Relationship match (e.g. "mom", "mother", "dad", "father")
            rel_map = {
                "mother": "mom",
                "mom": "mom",
                "mummy": "mom",
                "maa": "mom",
                "father": "dad",
                "dad": "dad",
                "papa": "dad"
            }
            if clean in rel_map:
                target_rel = rel_map[clean]
                matches = [c for c in all_contacts if (c.relationship and c.relationship.lower() == target_rel) or c.name.lower() == target_rel]
                if len(matches) == 1:
                    c = matches[0]
                    return {
                        "id": c.id,
                        "name": c.name,
                        "phone": c.phone,
                        "relationship": c.relationship,
                        "email": c.email
                    }, [{
                        "id": c.id,
                        "name": c.name,
                        "phone": c.phone,
                        "relationship": c.relationship,
                        "email": c.email
                    }]

            # 3. First name prefix / token match
            # e.g., "Ram" matches both "Ram Sharma" and "Ram Kumar"
            matches = []
            for c in all_contacts:
                c_name = c.name.lower()
                tokens = c_name.split()
                if clean in tokens or clean in c_name:
                    matches.append({
                        "id": c.id,
                        "name": c.name,
                        "phone": c.phone,
                        "relationship": c.relationship,
                        "email": c.email
                    })

            if len(matches) == 1:
                return matches[0], matches
            elif len(matches) > 1:
                # Ambiguous! Must ask user to select.
                return None, matches
            else:
                return None, []
        finally:
            db.close()


contact_service = ContactService()

# AI PM Permit SQL Helper
# Stores approved users for AI PM Permit feature

from sqlalchemy import Column, String, UnicodeText
from . import BASE, SESSION


class AiPmPermit(BASE):
    __tablename__ = "ai_pmpermit"
    user_id = Column(String(14), primary_key=True)
    first_name = Column(UnicodeText)
    username = Column(UnicodeText)

    def __init__(self, user_id, first_name, username):
        self.user_id = str(user_id)
        self.first_name = first_name
        self.username = username


AiPmPermit.__table__.create(checkfirst=True)


def ai_approve(user_id, first_name=None, username=None):
    """Approve a user for AI PM Permit."""
    to_check = is_ai_approved(user_id)
    if not to_check:
        user = AiPmPermit(str(user_id), first_name, username)
        SESSION.add(user)
        SESSION.commit()
        return True
    # Update existing record
    rem = SESSION.query(AiPmPermit).get(str(user_id))
    SESSION.delete(rem)
    SESSION.commit()
    user = AiPmPermit(str(user_id), first_name, username)
    SESSION.add(user)
    SESSION.commit()
    return True


def ai_disapprove(user_id):
    """Remove approval for a user."""
    to_check = is_ai_approved(user_id)
    if not to_check:
        return False
    rem = SESSION.query(AiPmPermit).get(str(user_id))
    SESSION.delete(rem)
    SESSION.commit()
    return True


def is_ai_approved(user_id):
    """Check if a user is approved."""
    try:
        if _result := SESSION.query(AiPmPermit).get(str(user_id)):
            return _result
        return None
    finally:
        SESSION.close()


def get_all_ai_approved():
    """Get all approved users."""
    try:
        return SESSION.query(AiPmPermit).all()
    except BaseException:
        return None
    finally:
        SESSION.close()


def ai_disapprove_all():
    """Remove all approvals."""
    try:
        SESSION.query(AiPmPermit).delete()
        SESSION.commit()
        return True
    except BaseException:
        return False
    finally:
        SESSION.close()

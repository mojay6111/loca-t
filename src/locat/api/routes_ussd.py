"""Africa's Talking USSD callback."""
from fastapi import APIRouter, Depends, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from locat.db.session import get_db
from locat.services.ussd_menu import handle_ussd

router = APIRouter(prefix="/ussd", tags=["ussd"])


@router.post("", response_class=PlainTextResponse)
def ussd_callback(
    sessionId: str = Form(""),
    serviceCode: str = Form(""),
    phoneNumber: str = Form(""),
    text: str = Form(""),
    db: Session = Depends(get_db),
):
    return handle_ussd(db, phoneNumber, text)
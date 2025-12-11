from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.errors import PaymentError
from app.schemas.payments import PayRequest, PayResponse
from app.services.payment_service import calculate_and_apply_payment

router = APIRouter(prefix="/api", tags=["payments"])


@router.post("/pay", response_model=PayResponse)
def pay(
    req: PayRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    cashier_client_id = request.headers.get("X-Cashier-Id", "CASHIER_DEV")
    client_ip = request.client.host if request.client else "unknown"

    try:
        with db.begin():
            txn, subsidy_rem, monthly_rem = calculate_and_apply_payment(
                db=db,
                card_uid=req.card_uid,
                canteen_id=req.canteen_id,
                amount_cents=req.amount_cents,
                liveness_token=req.liveness_token,
                cashier_client_id=cashier_client_id,
                client_ip=client_ip,
            )

        return PayResponse(
            status="APPROVED",
            transaction_id=txn.uuid,
            amount_total_cents=txn.amount_total_cents,
            subsidy_cents=txn.subsidy_cents,
            salary_cents=txn.salary_cents,
            today_subsidy_remaining_cents=subsidy_rem,
            monthly_remaining_cents=monthly_rem,
            error_code=None,
            message="Оплата успешно выполнена.",
        )
    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": e.code, "message": e.message},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "TECHNICAL_ERROR",
                "message": "Произошла техническая ошибка. Попробуйте позже.",
            },
        )

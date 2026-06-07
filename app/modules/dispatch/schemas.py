from pydantic import BaseModel


class DispatchResponse(BaseModel):
    order_id: int
    rider_id: int
    status: str
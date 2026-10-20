from typing import Optional, Dict, Any
from fastapi import FastAPI, Response, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

deliveries_db: Dict[int, Dict[str, Any]] = {}
current_id: int = 1

VALID_STATUSES = ["created", "in_transit", "delivered"]

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request body or validation error"}
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/deliveries", status_code=201)
async def create_delivery(request_data: Dict[str, Any] = None):
    global current_id
    
    if request_data is None or not isinstance(request_data, dict):
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
    
    recipient = request_data.get("recipient")
    address = request_data.get("address")
    
    if not recipient or not isinstance(recipient, str) or not recipient.strip():
        return JSONResponse(status_code=400, content={"error": "recipient must be a non-empty string"})
    if not address or not isinstance(address, str) or not address.strip():
        return JSONResponse(status_code=400, content={"error": "address must be a non-empty string"})
    
    new_delivery = {
        "id": current_id,
        "recipient": recipient,
        "address": address,
        "status": "created"
    }
    
    deliveries_db[current_id] = new_delivery
    current_id += 1
    
    return new_delivery

@app.get("/deliveries")
def get_deliveries(status: Optional[str] = None):
    if status is not None:
        if status not in VALID_STATUSES:
            return JSONResponse(status_code=400, content={"error": "Invalid status query parameter"})
        filtered = [d for d in deliveries_db.values() if d["status"] == status]
        return filtered
    
    return list(deliveries_db.values())

@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: int):
    if delivery_id not in deliveries_db:
        return JSONResponse(status_code=404, content={"error": "Delivery not found"})
    return deliveries_db[delivery_id]

@app.patch("/deliveries/{delivery_id}/status")
async def update_status(delivery_id: int, request_data: Dict[str, Any] = None):
    if delivery_id not in deliveries_db:
        return JSONResponse(status_code=404, content={"error": "Delivery not found"})
    
    if request_data is None or not isinstance(request_data, dict):
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
    
    new_status = request_data.get("status")
    if not new_status or new_status not in VALID_STATUSES:
        return JSONResponse(status_code=400, content={"error": "Invalid status value"})
    
    current_delivery = deliveries_db[delivery_id]
    current_status = current_delivery["status"]
    
    if current_status == "created" and new_status != "in_transit":
        return JSONResponse(status_code=409, content={"error": "Invalid status transition"})
    elif current_status == "in_transit" and new_status != "delivered":
        return JSONResponse(status_code=409, content={"error": "Invalid status transition"})
    elif current_status == "delivered":
        return JSONResponse(status_code=409, content={"error": "Cannot change status of delivered item"})
    
    current_delivery["status"] = new_status
    return current_delivery

@app.delete("/deliveries/{delivery_id}", status_code=204)
def delete_delivery(delivery_id: int):
    if delivery_id not in deliveries_db:
        return JSONResponse(status_code=404, content={"error": "Delivery not found"})
    
    if deliveries_db[delivery_id]["status"] != "created":
        return JSONResponse(status_code=409, content={"error": "Cannot delete delivery that is in transit or delivered"})
    
    del deliveries_db[delivery_id]
    return Response(status_code=204)
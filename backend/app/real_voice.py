import os
import json
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Twilio provides a way to control calls using TwiML (XML)
# and stream audio back and forth via WebSockets.
# To use this in production, you would run: pip install twilio

router = APIRouter()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
# Ngrok or production domain to handle Twilio webhooks
PUBLIC_DOMAIN = os.getenv("PUBLIC_DOMAIN", "your-ngrok-url.ngrok.app")


class DispatchCallRequest(BaseModel):
    lead_id: str
    campaign_id: str
    phone_number: str


@router.post("/api/v1/twilio/dispatch")
async def dispatch_twilio_call(body: DispatchCallRequest):
    """
    Step 1: Initiate an outbound call using Twilio's REST API.
    """
    if not TWILIO_ACCOUNT_SID:
        raise HTTPException(status_code=500, detail="Twilio credentials not configured.")
    
    # In a real app:
    # from twilio.rest import Client
    # client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    # 
    # call = client.calls.create(
    #     to=body.phone_number,
    #     from_=TWILIO_PHONE_NUMBER,
    #     # Twilio will fetch this URL when the lead picks up
    #     url=f"https://{PUBLIC_DOMAIN}/api/v1/twilio/twiml?lead_id={body.lead_id}",
    #     status_callback=f"https://{PUBLIC_DOMAIN}/api/v1/twilio/status",
    #     status_callback_event=['completed']
    # )
    
    return {"status": "dispatched", "message": "Twilio call initiated"}


@router.post("/api/v1/twilio/twiml")
async def handle_twiml(request: Request):
    """
    Step 2: When the user answers, Twilio requests instructions (TwiML).
    We instruct Twilio to open a bi-directional WebSocket audio stream.
    """
    # lead_id = request.query_params.get("lead_id")
    
    # The <Connect><Stream> verb tells Twilio to send raw audio to our WebSocket
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Connect>
            <Stream url="wss://{PUBLIC_DOMAIN}/api/v1/twilio/media-stream" />
        </Connect>
    </Response>
    """
    return HTMLResponse(content=twiml_response, media_type="text/xml")


@router.websocket("/api/v1/twilio/media-stream")
async def twilio_media_stream(websocket: WebSocket):
    """
    Step 3: Handle the raw audio from Twilio.
    This is where you integrate with OpenAI's Realtime API.
    """
    await websocket.accept()
    stream_sid = None
    
    try:
        # In a real app, you would also connect a WebSocket to OpenAI here.
        # openai_ws = await websockets.connect('wss://api.openai.com/v1/realtime?...')
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            event = message.get("event")
            
            if event == "start":
                stream_sid = message["start"]["streamSid"]
                # Call started. Send initial greeting audio back to Twilio.
                # (You would generate this via TTS or OpenAI)
                
            elif event == "media":
                # Received audio chunk from the phone call (Twilio sends base64 mulaw)
                inbound_audio_base64 = message["media"]["payload"]
                
                # Send this inbound_audio_base64 to OpenAI to process what the human is saying
                # ...
                
                # When OpenAI sends AI-generated audio back, you send it to Twilio like this:
                # out_msg = {
                #     "event": "media",
                #     "streamSid": stream_sid,
                #     "media": {"payload": base64_encoded_audio_from_llm}
                # }
                # await websocket.send_json(out_msg)
                
            elif event == "stop":
                # Call ended
                break
                
    except WebSocketDisconnect:
        print("Twilio WebSocket disconnected")


@router.post("/api/v1/twilio/status")
async def call_status_webhook(request: Request):
    """
    Step 4: Twilio calls this when the phone call is officially hung up.
    Here you create human handoff tasks or update the CRM.
    """
    form_data = await request.form()
    
    call_sid = form_data.get("CallSid")
    call_duration = form_data.get("CallDuration")
    call_status = form_data.get("CallStatus") # e.g., 'completed', 'busy', 'no-answer'
    
    # In a full implementation, you'd analyze the transcript generated in Step 3
    # to determine intent. For demonstration, we assume they asked for a human.
    intent = "Interested" 
    handoff_requested = True
    
    if call_status == "completed":
        if handoff_requested or intent == "Interested":
            # create_record("tasks", {
            #     "title": "Human Handoff Follow-up (Twilio)",
            #     "lead_id": "...", 
            #     "status": "open",
            #     "priority": "HIGH",
            #     "reason": f"Call SID {call_sid} completed. Prospect requested human."
            # })
            pass
            
    return {"received": True}

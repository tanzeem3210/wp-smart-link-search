from fastapi import FastAPI, UploadFile, File, HTTPException
from app.services.chat_parser import parse_chat


app = FastAPI(
    title = "Whatsapp quick link search",
    description = "For self use only",
    version = "1.0"
)

@app.get("/")
def home():
    return {"Status" : "Tanzeem"}

@app.post("/api/upload")
async def upload_chat(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code = 400,
            detail = "Please upload a Whatsapp .txt export.",
        )

    raw_content = await file.read()

    if len(raw_content) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 20 MB upload limit.",
        )

    content = raw_content.decode("utf-8-sig", errors="replace")
    messages = parse_chat(content)

    if not messages:
        raise HTTPException(
            status_code=422,
            detail="No messages recognized. Check the chat export format.",
        )

    links = [
        {
            "url": url,
            "timestamp": message["timestamp"],
            "sender": message["sender"],
            "message": message["text"],
        }
        for message in messages
        for url in message["links"]
    ]

    return {
        "filename": file.filename,
        "messages_parsed": len(messages),
        "links_found": len(links),
        "messages": messages,
        "links": links,
    }


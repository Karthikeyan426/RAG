from fastapi import APIRouter, Depends, Request, HTTPException
from database_config import SessionDep
from chats.models import question_model
from database_schema import chats, docs
from sentence_transformers import SentenceTransformer
from sqlmodel import select, text
from config import settings
from groq import Groq
from auth.current_user_extraction import get_current_user
from embedding_model import model

router = APIRouter(prefix='/users/user/chats', tags=['chats'])

@router.post('/query', status_code = 200)
async def processQuery(requestData: question_model.QModel, session: SessionDep, currentUser: str = Depends(get_current_user)):
    id = requestData.doc_id
    doc: docs = session.get(docs, requestData.doc_id)
    if not doc:
        raise HTTPException(status_code = 404, detail = "document not found")
    else:
        if doc.user_id != currentUser:
            raise HTTPException(status_code = 401, detail = "unauthorized document")


    qEmbedding = model.encode(requestData.question).tolist()
    similarQ = session.execute(
        text("""
            SELECT response_content
            FROM chats
            WHERE 1 - (question_embedding <=> CAST(:q_embedding AS vector)) > 0.80
            ORDER BY question_embedding <=> CAST(:q_embedding AS vector)
            LIMIT 1
        """),
        {"q_embedding": str(qEmbedding)}
    ).first()

    if similarQ:
        chat = chats(
            doc_id= requestData.doc_id,
            question_content = requestData.question,
            user_id = currentUser,
            response_content = similarQ.response_content,
        )
        session.add(chat)
        session.commit()
        session.refresh(chat)
        return {
            'id': chat.id,
            'question_content': chat.question_content,
            'response_content': chat.response_content,
            'queried_at': chat.queried_at
        }
    else:
        similarChunks = session.execute(
        text("""
            SELECT content, 1 - (embedding <=> CAST(:embedding AS vector))
            FROM chunks
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """),
        {"embedding": str(qEmbedding), "limit": 5}
        )

        context = "\n".join([chunk.content for chunk in similarChunks])
        client = Groq(api_key = settings.groq_api_key)
        response = client.chat.completions.create(
            model = "llama-3.1-8b-instant",
            messages = [
                {
                    "role": "system",
                    "content": f"Answer the question based on this context:\n{context}"
                },
                {
                    "role": "user",
                    "content": requestData.question
                }
            ]
        )

        receivedResponse = response.choices[0].message.content
        chat = chats(
            doc_id = requestData.doc_id,
            user_id = currentUser,
            question_content = requestData.question,
            question_embedding = qEmbedding,
            response_content = receivedResponse
        )
        session.add(chat)
        session.commit()
        session.refresh(chat)

        return {
            'id': chat.id,
            'question_content': chat.question_content,
            'response_content': chat.response_content,
            'queried_at': chat.queried_at
        }




    

@router.delete('/{chat_id}',status_code = 200)
async def deleteChat(chat_id: str, session: SessionDep, currentUser: str = Depends(get_current_user)):
    id = chat_id
    chat = session.get(chats, id)
    if not chat:
        raise HTTPException(status_code = 404, detail = "chat not found")
    else:
        if chat.user_id != currentUser:
            raise HTTPException(status_code = 401, detail = "unauthorized chat")
        
    session.delete(chat)
    session.commit()
    return {"message": "chat deleted", "id": id}



@router.get('/{chat_id}', status_code = 200)
async def getChat(chat_id: str, session: SessionDep, currentUser: str = Depends(get_current_user)):
    id = chat_id
    chat = session.exec(
        select(chats.id, chats.question_content, chats.response_content, chats.queried_at).where(chats.id == id)
    )
    if not chat:
        raise HTTPException(status_code = 404, detail = "chat not found")
    else:
        if chat.user_id != currentUser:
            raise HTTPException(status_code = 401, detail = "unauthorized chat")
        
    return {"chat_q": chat.question_content, "chat_a": chat.response_content}

@router.get("/doc/{doc_id}", status_code = 200)
async def getChats(doc_id: str, session: SessionDep, currentUser: str = Depends(get_current_user)):
    chatList = session.exec(
        select(chats.id, chats.question_content, chats.queried_at).where(chats.doc_id == doc_id).order_by(chats.queried_at.desc())
    ).all()
    if not chatList:
        raise HTTPException(status_code = 404, detail = "chats not found")
    else:
        return [
            {
                "id": row.id,
                "question_content": row.question_content,
                "queried_at": row.queried_at
            }
            for row in chatList
]

@router.get("/doc/recent/", status_code = 200)
async def getLastFiveChats(doc_id: str, last_chat_id: str, session: SessionDep, currentUser: str = Depends(get_current_user)):
    lastChat = session.get(chats, last_chat_id)
    if not lastChat:
        raise HTTPException(status_code = 402)
    recentChats = session.exec(
        select(chats.id, chats.question_content, chats.queried_at, chats.response_content).where((chats.doc_id == doc_id) & (chats.queried_at < lastChat.queried_at)).order_by(chats.queried_at.desc()).limit(5)
    ).all()
    if not recentChats:
        raise HTTPException(status_code = 404, detail = "chats not found")
    else:
        print(recentChats)
        return [
            {
                "id": row.id,
                "question_content": row.question_content,
                "response_content": row.response_content,
                "queried_at": row.queried_at
            }
            for row in recentChats
        ]
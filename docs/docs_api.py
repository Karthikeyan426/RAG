from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import insert
from auth.current_user_extraction import get_current_user
from database_config import SessionDep
from docs.models import doc_model
from database_schema import docs, chunks
from docs.helpers import doc_embedding_coversion, doc_text_extraction
from embedding_model import model
from config import settings
from sqlmodel import select

router = APIRouter(prefix="/users/user/docs", tags=["docs"])

@router.post('/upload', status_code = 201)
async def uploadDoc(session: SessionDep, currentUser: str = Depends(get_current_user), document: UploadFile = File(...)):
    uploadFile = document
    if uploadFile.content_type != "application/pdf":
        raise HTTPException(status_code = 400, detail = "file type not supported")
    else:
       doc = docs(doc_name = uploadFile.filename, user_id = currentUser)
       session.add(doc)
       session.commit()
       session.refresh(doc)


       text = doc_text_extraction.extractText(uploadFile.file)
       extracted_chunks = doc_embedding_coversion.chunk_text(text)
       
       embeddings = model.encode(
        extracted_chunks,
        batch_size = 32,
        show_progress_bar = True
       )

       print("saving chunks")
       chunksData = [
                  {
                      'doc_id': doc.id,
                      'embedding': embedding.tolist(),
                      'content': chunk
                  }
                  for chunk, embedding in zip(extracted_chunks, embeddings)
                ]
       session.execute(insert(chunks), chunksData)
       session.commit()
       return {"message": "document uploaded", "doc_id": doc.id}

       
       

@router.delete('/{doc_id}', status_code = 200)
async def deleteDoc(doc_id: str, session: SessionDep, currentUser: str = Depends(get_current_user)):
    id = doc_id
    doc = session.get(docs, id)
    if not doc:
        raise HTTPException(status_code = 404, detail = "document not found")
    else:
        if doc.user_id != currentUser:
            raise HTTPException(status_code = 401, detail = "unauthorized document")
    session.delete(doc)
    session.commit()
    return {"message": "document deleted"}
        

@router.post("",status_code = 200)
async def getUserDocs(session: SessionDep, currentUser: str = Depends(get_current_user)):
    user_id = currentUser
    docsList = session.exec(
        select(docs).where(docs.user_id == user_id)
    ).all()

    if not docsList:
        raise HTTPException(status_code = 404, detail = "documents not found")
    else:
        return {
            "docs": docsList
        }


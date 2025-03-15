from fastapi import APIRouter, Depends, BackgroundTasks, UploadFile, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.db import get_async_session, User, SearchSpace, Document, DocumentType
from app.schemas import DocumentsCreate, DocumentUpdate, DocumentRead
from app.users import current_active_user
from app.utils.check_ownership import check_ownership
from app.tasks.background_tasks import add_extension_received_document, add_received_file_document, add_crawled_url_document
from langchain_unstructured import UnstructuredLoader
from app.config import config
import json

router = APIRouter()

@router.post("/documents/")
async def create_documents(
    request: DocumentsCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
    fastapi_background_tasks: BackgroundTasks = BackgroundTasks()
):
    try:
        # Check if the user owns the search space
        await check_ownership(session, SearchSpace, request.search_space_id, user)
        
        if request.document_type == DocumentType.EXTENSION:
            for individual_document in request.content:
                fastapi_background_tasks.add_task(
                    add_extension_received_document, 
                    session, 
                    individual_document, 
                    request.search_space_id
                )
        elif request.document_type == DocumentType.CRAWLED_URL:
            for url in request.content:  
                fastapi_background_tasks.add_task(
                    add_crawled_url_document, 
                    session, 
                    url, 
                    request.search_space_id
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid document type"
            )
        
        await session.commit()
        return {"message": "Documents processed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process documents: {str(e)}"
        )

@router.post("/documents/fileupload")
async def create_documents(
    files: list[UploadFile],
    search_space_id: int = Form(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
    fastapi_background_tasks: BackgroundTasks = BackgroundTasks()
):
    try:
        await check_ownership(session, SearchSpace, search_space_id, user)
        
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
            
        for file in files:
            try:
                unstructured_loader = UnstructuredLoader(
                    file=file.file,
                    api_key=config.UNSTRUCTURED_API_KEY,
                    partition_via_api=True,
                    languages=["eng"],
                    include_orig_elements=False,
                    strategy="fast",
                )
                
                unstructured_processed_elements = await unstructured_loader.aload()
                
                fastapi_background_tasks.add_task(
                    add_received_file_document,
                    session,
                    file.filename,
                    unstructured_processed_elements,
                    search_space_id
                )
            except Exception as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Failed to process file {file.filename}: {str(e)}"
                )
        
        await session.commit()
        return {"message": "Files added for processing successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process documents: {str(e)}"
        )

@router.get("/documents/", response_model=List[DocumentRead])
async def read_documents(
    skip: int = 0,
    limit: int = 300,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    try:
        result = await session.execute(
            select(Document)
            .join(SearchSpace)
            .filter(SearchSpace.user_id == user.id)
            .offset(skip)
            .limit(limit)
        )
        db_documents = result.scalars().all()
        
        # Convert database objects to API-friendly format
        api_documents = []
        for doc in db_documents:
            api_documents.append(DocumentRead(
                id=doc.id,
                title=doc.title,
                document_type=doc.document_type,
                document_metadata=doc.document_metadata,
                content=doc.content,
                created_at=doc.created_at,
                search_space_id=doc.search_space_id
            ))
            
        return api_documents
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch documents: {str(e)}"
        )

@router.get("/documents/{document_id}", response_model=DocumentRead)
async def read_document(
    document_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    try:
        result = await session.execute(
            select(Document)
            .join(SearchSpace)
            .filter(Document.id == document_id, SearchSpace.user_id == user.id)
        )
        document = result.scalars().first()
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with id {document_id} not found"
            )
            
        # Convert database object to API-friendly format
        return DocumentRead(
            id=document.id,
            title=document.title,
            document_type=document.document_type,
            document_metadata=document.document_metadata,
            content=document.content,
            created_at=document.created_at,
            search_space_id=document.search_space_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch document: {str(e)}"
        )

@router.put("/documents/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    try:
        # Query the document directly instead of using read_document function
        result = await session.execute(
            select(Document)
            .join(SearchSpace)
            .filter(Document.id == document_id, SearchSpace.user_id == user.id)
        )
        db_document = result.scalars().first()
        
        if not db_document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with id {document_id} not found"
            )
            
        update_data = document_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_document, key, value)
        await session.commit()
        await session.refresh(db_document)
        
        # Convert to DocumentRead for response
        return DocumentRead(
            id=db_document.id,
            title=db_document.title,
            document_type=db_document.document_type,
            document_metadata=db_document.document_metadata,
            content=db_document.content,
            created_at=db_document.created_at,
            search_space_id=db_document.search_space_id
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update document: {str(e)}"
        )

@router.delete("/documents/{document_id}", response_model=dict)
async def delete_document(
    document_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    try:
        # Query the document directly instead of using read_document function
        result = await session.execute(
            select(Document)
            .join(SearchSpace)
            .filter(Document.id == document_id, SearchSpace.user_id == user.id)
        )
        document = result.scalars().first()
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with id {document_id} not found"
            )
            
        await session.delete(document)
        await session.commit()
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        ) 
"""
SearchSourceConnector routes for CRUD operations:
POST /search-source-connectors/ - Create a new connector
GET /search-source-connectors/ - List all connectors for the current user
GET /search-source-connectors/{connector_id} - Get a specific connector
PUT /search-source-connectors/{connector_id} - Update a specific connector
DELETE /search-source-connectors/{connector_id} - Delete a specific connector
POST /search-source-connectors/{connector_id}/index - Index content from a connector to a search space

Note: Each user can have only one connector of each type (SERPER_API, TAVILY_API, SLACK_CONNECTOR, NOTION_CONNECTOR).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any
from app.db import get_async_session, User, SearchSourceConnector, SearchSourceConnectorType, SearchSpace
from app.schemas import SearchSourceConnectorCreate, SearchSourceConnectorUpdate, SearchSourceConnectorRead
from app.users import current_active_user
from app.utils.check_ownership import check_ownership
from pydantic import ValidationError
from app.tasks.connectors_indexing_tasks import index_slack_messages, index_notion_pages
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/search-source-connectors/", response_model=SearchSourceConnectorRead)
async def create_search_source_connector(
    connector: SearchSourceConnectorCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """
    Create a new search source connector.
    
    Each user can have only one connector of each type (SERPER_API, TAVILY_API, SLACK_CONNECTOR).
    The config must contain the appropriate keys for the connector type.
    """
    try:
        # Check if a connector with the same type already exists for this user
        result = await session.execute(
            select(SearchSourceConnector)
            .filter(
                SearchSourceConnector.user_id == user.id,
                SearchSourceConnector.connector_type == connector.connector_type
            )
        )
        existing_connector = result.scalars().first()
        
        if existing_connector:
            raise HTTPException(
                status_code=409,
                detail=f"A connector with type {connector.connector_type} already exists. Each user can have only one connector of each type."
            )
            
        db_connector = SearchSourceConnector(**connector.model_dump(), user_id=user.id)
        session.add(db_connector)
        await session.commit()
        await session.refresh(db_connector)
        return db_connector
    except ValidationError as e:
        await session.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}"
        )
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Integrity error: A connector with this type already exists. {str(e)}"
        )
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create search source connector: {str(e)}"
        )

@router.get("/search-source-connectors/", response_model=List[SearchSourceConnectorRead])
async def read_search_source_connectors(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """List all search source connectors for the current user."""
    try:
        result = await session.execute(
            select(SearchSourceConnector)
            .filter(SearchSourceConnector.user_id == user.id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch search source connectors: {str(e)}"
        )

@router.get("/search-source-connectors/{connector_id}", response_model=SearchSourceConnectorRead)
async def read_search_source_connector(
    connector_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """Get a specific search source connector by ID."""
    try:
        return await check_ownership(session, SearchSourceConnector, connector_id, user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch search source connector: {str(e)}"
        )

@router.put("/search-source-connectors/{connector_id}", response_model=SearchSourceConnectorRead)
async def update_search_source_connector(
    connector_id: int,
    connector_update: SearchSourceConnectorUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """
    Update a search source connector.
    
    Each user can have only one connector of each type (SERPER_API, TAVILY_API, SLACK_CONNECTOR).
    The config must contain the appropriate keys for the connector type.
    """
    try:
        db_connector = await check_ownership(session, SearchSourceConnector, connector_id, user)
        
        # If connector type is being changed, check if one of that type already exists
        if connector_update.connector_type != db_connector.connector_type:
            result = await session.execute(
                select(SearchSourceConnector)
                .filter(
                    SearchSourceConnector.user_id == user.id,
                    SearchSourceConnector.connector_type == connector_update.connector_type,
                    SearchSourceConnector.id != connector_id
                )
            )
            existing_connector = result.scalars().first()
            
            if existing_connector:
                raise HTTPException(
                    status_code=409,
                    detail=f"A connector with type {connector_update.connector_type} already exists. Each user can have only one connector of each type."
                )
        
        update_data = connector_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_connector, key, value)
        await session.commit()
        await session.refresh(db_connector)
        return db_connector
    except ValidationError as e:
        await session.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}"
        )
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Integrity error: A connector with this type already exists. {str(e)}"
        )
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update search source connector: {str(e)}"
        )

@router.delete("/search-source-connectors/{connector_id}", response_model=dict)
async def delete_search_source_connector(
    connector_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user)
):
    """Delete a search source connector."""
    try:
        db_connector = await check_ownership(session, SearchSourceConnector, connector_id, user)
        await session.delete(db_connector)
        await session.commit()
        return {"message": "Search source connector deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete search source connector: {str(e)}"
        )

@router.post("/search-source-connectors/{connector_id}/index", response_model=Dict[str, Any])
async def index_connector_content(
    connector_id: int,
    search_space_id: int = Query(..., description="ID of the search space to store indexed content"),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
    background_tasks: BackgroundTasks = None
):
    """
    Index content from a connector to a search space.
    
    Currently supports:
    - SLACK_CONNECTOR: Indexes messages from all accessible Slack channels since the last indexing
      (or the last 365 days if never indexed before)
    - NOTION_CONNECTOR: Indexes pages from all accessible Notion pages since the last indexing
      (or the last 365 days if never indexed before)
    
    Args:
        connector_id: ID of the connector to use
        search_space_id: ID of the search space to store indexed content
        background_tasks: FastAPI background tasks
    
    Returns:
        Dictionary with indexing status
    """
    try:
        # Check if the connector belongs to the user
        connector = await check_ownership(session, SearchSourceConnector, connector_id, user)
        
        # Check if the search space belongs to the user
        search_space = await check_ownership(session, SearchSpace, search_space_id, user)
        
        # Handle different connector types
        if connector.connector_type == SearchSourceConnectorType.SLACK_CONNECTOR:
            # Determine the time range that will be indexed
            if not connector.last_indexed_at:
                start_date = "365 days ago"
            else:
                # Check if last_indexed_at is today
                today = datetime.now().date()
                if connector.last_indexed_at.date() == today:
                    # If last indexed today, go back 1 day to ensure we don't miss anything
                    start_date = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                else:
                    start_date = connector.last_indexed_at.strftime("%Y-%m-%d")
            
            # Add the indexing task to background tasks
            if background_tasks:
                background_tasks.add_task(
                    run_slack_indexing,
                    session,
                    connector_id,
                    search_space_id
                )
                
                return {
                    "success": True,
                    "message": "Slack indexing started in the background",
                    "connector_type": connector.connector_type,
                    "search_space": search_space.name,
                    "indexing_from": start_date,
                    "indexing_to": datetime.now().strftime("%Y-%m-%d")
                }
            else:
                # For testing or if background tasks are not available
                return {
                    "success": False,
                    "message": "Background tasks not available",
                    "connector_type": connector.connector_type
                }
        elif connector.connector_type == SearchSourceConnectorType.NOTION_CONNECTOR:
            # Determine the time range that will be indexed
            if not connector.last_indexed_at:
                start_date = "365 days ago"
            else:
                # Check if last_indexed_at is today
                today = datetime.now().date()
                if connector.last_indexed_at.date() == today:
                    # If last indexed today, go back 1 day to ensure we don't miss anything
                    start_date = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                else:
                    start_date = connector.last_indexed_at.strftime("%Y-%m-%d")
            
            # Add the indexing task to background tasks
            if background_tasks:
                background_tasks.add_task(
                    run_notion_indexing,
                    session,
                    connector_id,
                    search_space_id
                )
                
                return {
                    "success": True,
                    "message": "Notion indexing started in the background",
                    "connector_type": connector.connector_type,
                    "search_space": search_space.name,
                    "indexing_from": start_date,
                    "indexing_to": datetime.now().strftime("%Y-%m-%d")
                }
            else:
                # For testing or if background tasks are not available
                return {
                    "success": False,
                    "message": "Background tasks not available",
                    "connector_type": connector.connector_type
                }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Indexing not supported for connector type: {connector.connector_type}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start indexing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start indexing: {str(e)}"
        ) 
        
        
async def update_connector_last_indexed(
    session: AsyncSession,
    connector_id: int
):
    """
    Update the last_indexed_at timestamp for a connector.
    
    Args:
        session: Database session
        connector_id: ID of the connector to update
    """
    try:
        result = await session.execute(
            select(SearchSourceConnector)
            .filter(SearchSourceConnector.id == connector_id)
        )
        connector = result.scalars().first()
        
        if connector:
            connector.last_indexed_at = datetime.now()
            await session.commit()
            logger.info(f"Updated last_indexed_at for connector {connector_id}")
    except Exception as e:
        logger.error(f"Failed to update last_indexed_at for connector {connector_id}: {str(e)}")
        await session.rollback()

async def run_slack_indexing(
    session: AsyncSession,
    connector_id: int,
    search_space_id: int
):
    """
    Background task to run Slack indexing.
    
    Args:
        session: Database session
        connector_id: ID of the Slack connector
        search_space_id: ID of the search space
    """
    try:
        # Index Slack messages without updating last_indexed_at (we'll do it separately)
        documents_indexed, error_or_warning = await index_slack_messages(
            session=session,
            connector_id=connector_id,
            search_space_id=search_space_id,
            update_last_indexed=False  # Don't update timestamp in the indexing function
        )
        
        # Only update last_indexed_at if indexing was successful
        if documents_indexed > 0 and (error_or_warning is None or "Indexed" in error_or_warning):
            await update_connector_last_indexed(session, connector_id)
            logger.info(f"Slack indexing completed successfully: {documents_indexed} documents indexed")
        else:
            logger.error(f"Slack indexing failed or no documents indexed: {error_or_warning}")
    except Exception as e:
        logger.error(f"Error in background Slack indexing task: {str(e)}")

async def run_notion_indexing(
    session: AsyncSession,
    connector_id: int,
    search_space_id: int
):
    """
    Background task to run Notion indexing.
    
    Args:
        session: Database session
        connector_id: ID of the Notion connector
        search_space_id: ID of the search space
    """
    try:
        # Index Notion pages without updating last_indexed_at (we'll do it separately)
        documents_indexed, error_or_warning = await index_notion_pages(
            session=session,
            connector_id=connector_id,
            search_space_id=search_space_id,
            update_last_indexed=False  # Don't update timestamp in the indexing function
        )
        
        # Only update last_indexed_at if indexing was successful
        if documents_indexed > 0 and (error_or_warning is None or "Indexed" in error_or_warning):
            await update_connector_last_indexed(session, connector_id)
            logger.info(f"Notion indexing completed successfully: {documents_indexed} documents indexed")
        else:
            logger.error(f"Notion indexing failed or no documents indexed: {error_or_warning}")
    except Exception as e:
        logger.error(f"Error in background Notion indexing task: {str(e)}")
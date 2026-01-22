"""
Visual API Routes - Handle visual generation and retrieval
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from app.services.visual_generation import visual_service
from app.models.visual import Visual, VisualTemplate


router = APIRouter(prefix="/visuals", tags=["Visuals"])


class VisualGenerateRequest(BaseModel):
    concept: str
    visual_type: str = "animation"  # animation, image, diagram
    description: Optional[str] = None


@router.post("/generate")
async def generate_visual(request: VisualGenerateRequest):
    """Generate a visual demonstration for a concept"""
    
    try:
        visual_spec = {
            "description": request.description or f"Visual demonstration of {request.concept}",
            "type": request.visual_type
        }
        
        result = await visual_service.generate_visual(
            visual_spec=visual_spec,
            concept=request.concept,
            visual_type=request.visual_type
        )
        
        # Save to database
        visual = Visual(
            title=f"Visual: {request.concept[:50]}",
            description=request.description or "",
            visual_type=result.get("visual_type", request.visual_type),
            concept=request.concept,
            full_url=result.get("url", ""),
            generation_method="ai",
            generation_prompt=request.description
        )
        await visual.insert()
        
        return {
            "visual_id": str(visual.id),
            "visual_type": result.get("visual_type"),
            "url": result.get("url"),
            "local_path": result.get("local_path"),
            "format": result.get("format")
        }
        
    except Exception as e:
        logger.error(f"Error generating visual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate visual: {str(e)}"
        )


@router.get("/{visual_id}")
async def get_visual(visual_id: str):
    """Get a specific visual by ID"""
    
    visual = await Visual.get(visual_id)
    
    if not visual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visual not found"
        )
    
    # Increment view count
    visual.view_count += 1
    await visual.save()
    
    return {
        "visual_id": str(visual.id),
        "title": visual.title,
        "description": visual.description,
        "visual_type": visual.visual_type,
        "concept": visual.concept,
        "url": visual.full_url,
        "thumbnail_url": visual.thumbnail_url,
        "duration_seconds": visual.duration_seconds,
        "view_count": visual.view_count
    }


@router.get("/search/concept")
async def search_visuals_by_concept(
    concept: str,
    visual_type: Optional[str] = None,
    limit: int = 10
):
    """Search for existing visuals by concept"""
    
    query = Visual.find(
        {"$text": {"$search": concept}},
        {"score": {"$meta": "textScore"}}
    )
    
    if visual_type:
        query = query.find(Visual.visual_type == visual_type)
    
    visuals = await query.sort([("score", {"$meta": "textScore"})]).limit(limit).to_list()
    
    return [
        {
            "visual_id": str(v.id),
            "title": v.title,
            "concept": v.concept,
            "visual_type": v.visual_type,
            "url": v.full_url,
            "thumbnail_url": v.thumbnail_url
        }
        for v in visuals
    ]


@router.get("/templates/list")
async def list_visual_templates(
    subject: Optional[str] = None,
    limit: int = 20
):
    """List available visual templates"""
    
    query = VisualTemplate.find(VisualTemplate.is_active == True)
    
    if subject:
        query = query.find(VisualTemplate.subject == subject)
    
    templates = await query.limit(limit).to_list()
    
    return [
        {
            "template_id": str(t.id),
            "name": t.name,
            "description": t.description,
            "concept": t.concept,
            "subject": t.subject,
            "template_type": t.template_type,
            "preview_url": t.preview_url,
            "use_count": t.use_count
        }
        for t in templates
    ]


@router.post("/templates/{template_id}/generate")
async def generate_from_template(
    template_id: str,
    parameters: Optional[dict] = None
):
    """Generate a visual from a template with custom parameters"""
    
    template = await VisualTemplate.get(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    try:
        # TODO: Implement template-based generation
        # This would involve:
        # 1. Loading the template code
        # 2. Applying custom parameters
        # 3. Rendering the visual
        
        # Update use count
        template.use_count += 1
        await template.save()
        
        return {
            "message": "Template-based generation not yet implemented",
            "template_id": template_id,
            "template_name": template.name
        }
        
    except Exception as e:
        logger.error(f"Error generating from template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate from template: {str(e)}"
        )

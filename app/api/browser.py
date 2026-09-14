from fastapi import APIRouter
router = APIRouter(prefix="/api/browser", tags=["浏览器测试"])


@router.get("/screenshots")
async def list_screenshots() -> Dict[str, Any]:
    """List all screenshots."""
    import os
    screenshot_dir = "/tmp/testpilot-pro/screenshots"
    screenshots = []
    
    if os.path.exists(screenshot_dir):
        for filename in os.listdir(screenshot_dir):
            if filename.endswith(('.png', '.jpg', '.jpeg')):
                filepath = os.path.join(screenshot_dir, filename)
                screenshots.append({
                    "id": filename,
                    "name": filename,
                    "path": f"/screenshots/{filename}",
                    "created_at": os.path.getmtime(filepath)
                })
    
    screenshots.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "screenshots": screenshots,
        "total": len(screenshots)
    }

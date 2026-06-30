import logging

from core.model_router import model_router, TaskClass

logger = logging.getLogger("nexus.vision_parser")

class VisionParser:
    """
    Handles screenshot analysis using Set-of-Mark overlay generation
    and multimodal LLM querying.
    """
    
    async def analyze_screenshot(
        self, 
        base64_image: str, 
        prompt: str, 
        use_som: bool = False
    ) -> str:
        """
        Sends an image to the Vision tier (e.g. Gemini 2.0 Flash) to answer a prompt.
        If use_som is True, applies Set-of-Mark bounding boxes first.
        """
        if use_som:
            # Future enhancement: apply numeric bounding boxes using OmniParser or OpenCV
            # For now, pass raw image.
            logger.debug("Set-of-Mark annotation requested. (Placeholder logic)")
            pass
            
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ]
        
        try:
            logger.info("👀 Dispatching image to VISION tier...")
            result = await model_router.route_task(
                task_class=TaskClass.VISION,
                system_prompt="You are Nexus Vision.",
                messages=messages
            )
            return result
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return f"Error: Vision pipeline failed - {e}"

vision_parser = VisionParser()

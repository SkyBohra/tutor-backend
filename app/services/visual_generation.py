"""
Visual Generation Service - Creates visual demonstrations for educational content
Supports multiple generation methods: Manim animations, AI image generation, diagrams
"""

import os
import json
import asyncio
import tempfile
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path
import httpx
from loguru import logger
from app.core.config import settings


class VisualGenerationService:
    """Service for generating visual demonstrations"""
    
    def __init__(self):
        self.replicate_token = settings.REPLICATE_API_TOKEN
        self.stability_api_key = settings.STABILITY_API_KEY
        self.temp_dir = Path(tempfile.gettempdir()) / "ai_teacher_visuals"
        self.temp_dir.mkdir(exist_ok=True)
    
    async def generate_visual(
        self,
        visual_spec: Dict[str, Any],
        concept: str,
        visual_type: str = "animation"
    ) -> Dict[str, Any]:
        """
        Main method to generate a visual based on specification
        
        Args:
            visual_spec: Visual specification from AI explanation service
            concept: The concept being explained
            visual_type: Type of visual (animation, image, diagram)
        
        Returns:
            Dict with visual URL and metadata
        """
        
        if visual_type == "animation":
            return await self._generate_animation(visual_spec, concept)
        elif visual_type == "image":
            return await self._generate_image(visual_spec, concept)
        elif visual_type == "diagram":
            return await self._generate_diagram(visual_spec, concept)
        else:
            return await self._generate_image(visual_spec, concept)
    
    async def _generate_animation(
        self,
        visual_spec: Dict[str, Any],
        concept: str
    ) -> Dict[str, Any]:
        """Generate animation using Manim or Lottie"""
        
        # Check if we have Manim code in the spec
        manim_code = visual_spec.get("manim_code")
        
        if manim_code:
            return await self._render_manim_animation(manim_code, concept)
        
        # Otherwise, generate a simple animation using templates
        return await self._generate_template_animation(visual_spec, concept)
    
    async def _render_manim_animation(
        self,
        manim_code: str,
        concept: str
    ) -> Dict[str, Any]:
        """Render a Manim animation from Python code"""
        
        try:
            # Create a temporary Python file with the Manim code
            scene_name = concept.replace(" ", "").replace("?", "")[:20] + "Scene"
            
            # Wrap the code in a proper Manim scene if not already
            if "class" not in manim_code:
                manim_code = self._wrap_manim_code(manim_code, scene_name)
            
            temp_file = self.temp_dir / f"{scene_name}.py"
            temp_file.write_text(manim_code)
            
            # Render the animation
            output_dir = self.temp_dir / "outputs"
            output_dir.mkdir(exist_ok=True)
            
            # Run Manim to render the animation
            process = await asyncio.create_subprocess_exec(
                "manim",
                str(temp_file),
                scene_name,
                "-qm",  # Medium quality
                "-o", f"{scene_name}.mp4",
                "--media_dir", str(output_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Manim rendering failed: {stderr.decode()}")
                # Fall back to image generation
                return await self._generate_fallback_visual(concept)
            
            # Find the output file
            output_file = output_dir / "videos" / scene_name / "720p30" / f"{scene_name}.mp4"
            
            if output_file.exists():
                # TODO: Upload to S3 and return URL
                return {
                    "visual_type": "animation",
                    "local_path": str(output_file),
                    "url": f"/media/animations/{scene_name}.mp4",  # Placeholder
                    "duration_seconds": 10,  # Estimate
                    "format": "mp4"
                }
            else:
                return await self._generate_fallback_visual(concept)
                
        except Exception as e:
            logger.error(f"Error rendering Manim animation: {e}")
            return await self._generate_fallback_visual(concept)
    
    def _wrap_manim_code(self, code: str, scene_name: str) -> str:
        """Wrap raw Manim code in a proper scene class"""
        
        return f'''from manim import *

class {scene_name}(Scene):
    def construct(self):
        {code}
'''
    
    async def _generate_template_animation(
        self,
        visual_spec: Dict[str, Any],
        concept: str
    ) -> Dict[str, Any]:
        """Generate animation from pre-defined templates"""
        
        # Get the animation type from visual spec
        description = visual_spec.get("description", "")
        elements = visual_spec.get("elements", [])
        
        # Use template-based generation
        template = self._select_animation_template(description, concept)
        
        if template:
            return await self._render_manim_animation(template, concept)
        
        # Fall back to image generation
        return await self._generate_image(visual_spec, concept)
    
    def _select_animation_template(
        self,
        description: str,
        concept: str
    ) -> Optional[str]:
        """Select appropriate animation template based on concept"""
        
        concept_lower = concept.lower()
        
        # Physics templates
        if "gravity" in concept_lower or "falling" in concept_lower:
            return self._get_gravity_template()
        elif "pendulum" in concept_lower:
            return self._get_pendulum_template()
        elif "wave" in concept_lower:
            return self._get_wave_template()
        elif "projectile" in concept_lower:
            return self._get_projectile_template()
        
        # Math templates
        elif "graph" in concept_lower or "function" in concept_lower:
            return self._get_graph_template()
        elif "circle" in concept_lower or "area" in concept_lower:
            return self._get_geometry_template()
        
        return None
    
    def _get_gravity_template(self) -> str:
        """Template for gravity/falling object animation"""
        return '''
# Gravity demonstration
title = Text("Gravity - Objects Fall Due to Earth's Pull", font_size=32)
self.play(Write(title))
self.wait(1)
self.play(title.animate.to_edge(UP))

# Draw ground
ground = Line(LEFT * 5, RIGHT * 5, color=GREEN).to_edge(DOWN, buff=0.5)
self.play(Create(ground))

# Create an apple
apple = Circle(radius=0.3, color=RED, fill_opacity=1).shift(UP * 3)
apple_label = Text("Apple", font_size=20).next_to(apple, RIGHT)
self.play(Create(apple), Write(apple_label))

# Show gravity arrow
gravity_arrow = Arrow(apple.get_center(), apple.get_center() + DOWN * 1.5, color=YELLOW)
gravity_label = Text("Gravity Force", font_size=18, color=YELLOW).next_to(gravity_arrow, RIGHT)
self.play(Create(gravity_arrow), Write(gravity_label))
self.wait(1)

# Remove labels for falling animation
self.play(FadeOut(apple_label), FadeOut(gravity_arrow), FadeOut(gravity_label))

# Animate falling
self.play(
    apple.animate.move_to(ground.get_center() + UP * 0.3),
    rate_func=rate_functions.ease_in_quad,
    run_time=2
)

# Show impact
impact = Text("9.8 m/s² acceleration", font_size=24, color=YELLOW).to_edge(DOWN, buff=1.5)
self.play(Write(impact))
self.wait(2)
'''
    
    def _get_pendulum_template(self) -> str:
        """Template for pendulum animation"""
        return '''
# Pendulum demonstration
title = Text("Simple Pendulum Motion", font_size=32)
self.play(Write(title))
self.wait(1)
self.play(title.animate.to_edge(UP))

# Pivot point
pivot = Dot(UP * 2.5, color=WHITE)
self.play(Create(pivot))

# Pendulum parameters
length = 3
angle = PI / 4

# Create pendulum
bob = Circle(radius=0.3, color=BLUE, fill_opacity=1)
string = Line(pivot.get_center(), pivot.get_center() + DOWN * length)
bob.move_to(string.get_end())

self.play(Create(string), Create(bob))
self.wait(0.5)

# Swing animation
for i in range(3):
    # Swing to right
    self.play(
        Rotate(VGroup(string, bob), angle=-angle, about_point=pivot.get_center()),
        rate_func=rate_functions.ease_in_out_sine,
        run_time=1
    )
    # Swing to left
    self.play(
        Rotate(VGroup(string, bob), angle=2*angle, about_point=pivot.get_center()),
        rate_func=rate_functions.ease_in_out_sine,
        run_time=2
    )
    # Swing back
    self.play(
        Rotate(VGroup(string, bob), angle=-angle, about_point=pivot.get_center()),
        rate_func=rate_functions.ease_in_out_sine,
        run_time=1
    )

# Explanation
explanation = Text("Period depends on length, not mass!", font_size=24, color=YELLOW)
explanation.to_edge(DOWN)
self.play(Write(explanation))
self.wait(2)
'''
    
    def _get_wave_template(self) -> str:
        """Template for wave animation"""
        return '''
# Wave demonstration
title = Text("Wave Motion", font_size=32)
self.play(Write(title))
self.wait(1)
self.play(title.animate.to_edge(UP))

# Create wave
axes = Axes(
    x_range=[0, 4 * PI, PI / 2],
    y_range=[-2, 2, 1],
    axis_config={"include_tip": True}
).scale(0.8)

def wave_func(x):
    return np.sin(x)

wave = axes.plot(wave_func, color=BLUE)
self.play(Create(axes))
self.play(Create(wave), run_time=2)

# Show wavelength
wavelength_brace = Brace(Line(axes.c2p(0, 0), axes.c2p(2 * PI, 0)), UP, color=YELLOW)
wavelength_label = wavelength_brace.get_text("Wavelength (λ)")
self.play(Create(wavelength_brace), Write(wavelength_label))

# Show amplitude
amplitude_arrow = DoubleArrow(axes.c2p(PI/2, 0), axes.c2p(PI/2, 1), color=GREEN)
amplitude_label = Text("Amplitude", font_size=20, color=GREEN).next_to(amplitude_arrow, RIGHT)
self.play(Create(amplitude_arrow), Write(amplitude_label))

self.wait(2)
'''
    
    def _get_projectile_template(self) -> str:
        """Template for projectile motion"""
        return '''
# Projectile motion
title = Text("Projectile Motion", font_size=32)
self.play(Write(title))
self.wait(1)
self.play(title.animate.to_edge(UP))

# Ground
ground = Line(LEFT * 6, RIGHT * 6, color=GREEN).to_edge(DOWN, buff=0.5)
self.play(Create(ground))

# Projectile (ball)
ball = Circle(radius=0.2, color=ORANGE, fill_opacity=1)
start_pos = LEFT * 5 + DOWN * 2
ball.move_to(start_pos)
self.play(Create(ball))

# Trajectory path
trajectory = ParametricFunction(
    lambda t: np.array([
        start_pos[0] + t * 2,
        start_pos[1] + t * 2 - 0.4 * t ** 2,
        0
    ]),
    t_range=[0, 5],
    color=YELLOW
).set_stroke(opacity=0.5)

# Animate projectile along path
self.play(MoveAlongPath(ball, trajectory), run_time=3)

# Draw the traced path
self.play(Create(trajectory))

# Labels
h_max = Text("Maximum Height", font_size=20).move_to(UP * 1.5)
range_text = Text("Range", font_size=20).next_to(ground, UP).shift(RIGHT * 2)
self.play(Write(h_max), Write(range_text))

self.wait(2)
'''
    
    def _get_graph_template(self) -> str:
        """Template for mathematical graph"""
        return '''
# Graph demonstration
title = Text("Mathematical Function Graph", font_size=32)
self.play(Write(title))
self.wait(1)
self.play(title.animate.to_edge(UP))

# Create coordinate system
axes = Axes(
    x_range=[-4, 4, 1],
    y_range=[-2, 8, 2],
    axis_config={"include_tip": True, "include_numbers": True}
).scale(0.7)

labels = axes.get_axis_labels(x_label="x", y_label="y")
self.play(Create(axes), Write(labels))

# Plot function
def func(x):
    return x ** 2

graph = axes.plot(func, color=BLUE, x_range=[-2.5, 2.5])
graph_label = MathTex("f(x) = x^2").next_to(graph, UR).set_color(BLUE)

self.play(Create(graph), Write(graph_label), run_time=2)

# Show a point
point = Dot(axes.c2p(1.5, func(1.5)), color=RED)
point_label = MathTex("(1.5, 2.25)").next_to(point, UR).scale(0.7)
self.play(Create(point), Write(point_label))

self.wait(2)
'''
    
    def _get_geometry_template(self) -> str:
        """Template for geometry concepts"""
        return '''
# Geometry demonstration
title = Text("Circle - Area and Circumference", font_size=32)
self.play(Write(title))
self.wait(1)
self.play(title.animate.to_edge(UP))

# Create circle
circle = Circle(radius=2, color=BLUE)
center = Dot(ORIGIN, color=WHITE)
center_label = Text("Center", font_size=16).next_to(center, DOWN, buff=0.1)

self.play(Create(circle), Create(center), Write(center_label))

# Show radius
radius = Line(ORIGIN, RIGHT * 2, color=YELLOW)
radius_label = MathTex("r").next_to(radius, UP).set_color(YELLOW)
self.play(Create(radius), Write(radius_label))

# Area formula
area_formula = MathTex("Area = \\pi r^2", color=GREEN).to_edge(DOWN, buff=1.5).shift(LEFT * 3)
self.play(Write(area_formula))

# Fill circle to show area
circle_fill = Circle(radius=2, color=GREEN, fill_opacity=0.3)
self.play(Create(circle_fill))

# Circumference
circumference_formula = MathTex("Circumference = 2\\pi r", color=ORANGE).to_edge(DOWN, buff=1.5).shift(RIGHT * 3)
self.play(Write(circumference_formula))

self.wait(2)
'''
    
    async def _generate_image(
        self,
        visual_spec: Dict[str, Any],
        concept: str
    ) -> Dict[str, Any]:
        """Generate an educational image using AI image generation"""
        
        description = visual_spec.get("description", f"Educational illustration of {concept}")
        
        # Build prompt for image generation
        prompt = self._build_image_prompt(description, concept)
        
        try:
            # Try Stability AI first
            if self.stability_api_key:
                return await self._generate_stability_image(prompt, concept)
            
            # Fall back to Replicate
            if self.replicate_token:
                return await self._generate_replicate_image(prompt, concept)
            
            # If no API keys, return placeholder
            return self._get_placeholder_visual(concept)
            
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return self._get_placeholder_visual(concept)
    
    def _build_image_prompt(self, description: str, concept: str) -> str:
        """Build prompt for AI image generation"""
        
        return f"""Educational illustration for teaching: {concept}

{description}

Style: Clean, professional educational diagram with clear labels.
Colors: Bright, engaging colors suitable for students.
Background: Simple white or light gradient background.
Text: Include minimal text labels where helpful.

The image should be clear, accurate, and help students understand the concept visually."""
    
    async def _generate_stability_image(
        self,
        prompt: str,
        concept: str
    ) -> Dict[str, Any]:
        """Generate image using Stability AI"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Authorization": f"Bearer {self.stability_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "text_prompts": [{"text": prompt}],
                    "cfg_scale": 7,
                    "height": 1024,
                    "width": 1024,
                    "samples": 1,
                    "steps": 30
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                # TODO: Save image and upload to S3
                return {
                    "visual_type": "image",
                    "url": "generated_image_url",  # Placeholder
                    "format": "png"
                }
            else:
                raise Exception(f"Stability AI error: {response.status_code}")
    
    async def _generate_replicate_image(
        self,
        prompt: str,
        concept: str
    ) -> Dict[str, Any]:
        """Generate image using Replicate"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Token {self.replicate_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "version": "stability-ai/sdxl:latest",
                    "input": {
                        "prompt": prompt,
                        "width": 1024,
                        "height": 1024
                    }
                }
            )
            
            if response.status_code == 201:
                # TODO: Poll for completion and get result
                return {
                    "visual_type": "image",
                    "url": "replicate_image_url",  # Placeholder
                    "format": "png"
                }
            else:
                raise Exception(f"Replicate error: {response.status_code}")
    
    async def _generate_diagram(
        self,
        visual_spec: Dict[str, Any],
        concept: str
    ) -> Dict[str, Any]:
        """Generate a diagram using matplotlib or similar"""
        
        # For now, fall back to image generation
        return await self._generate_image(visual_spec, concept)
    
    async def _generate_fallback_visual(
        self,
        concept: str
    ) -> Dict[str, Any]:
        """Generate a fallback visual when other methods fail"""
        
        return {
            "visual_type": "placeholder",
            "url": f"https://via.placeholder.com/800x600/4A90D9/FFFFFF?text={concept.replace(' ', '+')}",
            "message": "Visual generation in progress",
            "format": "png"
        }
    
    def _get_placeholder_visual(self, concept: str) -> Dict[str, Any]:
        """Get placeholder visual"""
        
        return {
            "visual_type": "placeholder",
            "url": f"https://via.placeholder.com/800x600/4A90D9/FFFFFF?text={concept.replace(' ', '+')}",
            "format": "png"
        }


# Singleton instance
visual_service = VisualGenerationService()

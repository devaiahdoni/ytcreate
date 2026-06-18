import os
from typing import TypedDict, List, Dict, Any, Optional
from pathlib import Path
import uuid

# LangGraph imports
from langgraph.graph import StateGraph, END

# Import Agents and Services
from config.settings import settings
from database.repository import init_db, VideoJobRepository, SceneRepository, async_session
from services.openai_service import OpenAIService
from services.gemini_service import GeminiService
from services.flow_service import FlowService
from services.tts_service import TTSService
from services.youtube_service import YouTubeService

from agents.script_agent import ScriptAgent
from agents.scene_agent import SceneAgent
from agents.prompt_agent import PromptAgent
from agents.voice_agent import VoiceAgent, VoiceGenerationAgent
from agents.composer_agent import ComposerAgent
from agents.thumbnail_agent import ThumbnailAgent
from agents.seo_agent import SEOAgent
from agents.youtube_agent import YouTubeAgent

from loguru import logger

# 1. Define State structure
class PipelineState(TypedDict):
    job_id: uuid.UUID
    topic: str
    status: str
    
    # Script details
    title: str
    hook: str
    full_script: str
    
    # Scenes metadata list
    # Each scene: {"scene_number": int, "voice_text": str, "visual_description": str, "duration": float, "id": int, ...}
    scenes: List[Dict[str, Any]]
    
    # Render and Upload assets
    final_video_path: str
    thumbnail_prompt: str
    thumbnail_path: str
    
    # SEO Details
    youtube_title: str
    youtube_description: str
    youtube_tags: List[str]
    
    # Output Upload
    youtube_video_id: str
    error: str

# 2. Define the Orchestrator Class
class PipelineOrchestrator:
    def __init__(self):
        # Initialize Services
        self.openai_service = OpenAIService()
        self.gemini_service = GeminiService()
        self.flow_service = FlowService()
        self.tts_service = TTSService()
        self.youtube_service = YouTubeService()
        
        # Initialize Agents
        self.script_agent = ScriptAgent(self.openai_service)
        self.scene_agent = SceneAgent(self.openai_service)
        self.prompt_agent = PromptAgent(self.openai_service)
        self.voice_agent = VoiceAgent(self.openai_service)
        self.voice_gen_agent = VoiceGenerationAgent(self.tts_service)
        self.composer_agent = ComposerAgent()
        self.thumbnail_agent = ThumbnailAgent(self.openai_service)
        self.seo_agent = SEOAgent(self.openai_service)
        self.youtube_agent = YouTubeAgent(self.youtube_service)
        
        # Build the LangGraph State Machine
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        workflow = StateGraph(PipelineState)

        # Add Nodes
        workflow.add_node("script_writing", self.script_writing_node)
        workflow.add_node("scene_splitting", self.scene_splitting_node)
        workflow.add_node("scene_prompting", self.scene_prompting_node)
        workflow.add_node("voice_narration", self.voice_narration_node)
        workflow.add_node("video_generation", self.video_generation_node)
        workflow.add_node("audio_generation", self.audio_generation_node)
        workflow.add_node("scene_compositing", self.scene_compositing_node)
        workflow.add_node("final_video_assembly", self.final_video_assembly_node)
        workflow.add_node("thumbnail_generation", self.thumbnail_generation_node)
        workflow.add_node("seo_optimization", self.seo_optimization_node)
        workflow.add_node("youtube_upload", self.youtube_upload_node)

        # Set Entry Point
        workflow.set_entry_point("script_writing")

        # Set Transitions
        workflow.add_edge("script_writing", "scene_splitting")
        workflow.add_edge("scene_splitting", "scene_prompting")
        workflow.add_edge("scene_prompting", "voice_narration")
        workflow.add_edge("voice_narration", "video_generation")
        workflow.add_edge("video_generation", "audio_generation")
        workflow.add_edge("audio_generation", "scene_compositing")
        workflow.add_edge("scene_compositing", "final_video_assembly")
        workflow.add_edge("final_video_assembly", "thumbnail_generation")
        workflow.add_edge("thumbnail_generation", "seo_optimization")
        workflow.add_edge("seo_optimization", "youtube_upload")
        workflow.add_edge("youtube_upload", END)

        return workflow.compile()

    # --- NODE IMPLEMENTATIONS ---

    async def script_writing_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: Script Writing ---")
        job_id = state["job_id"]
        
        async with async_session() as session:
            job_repo = VideoJobRepository(session)
            job = await job_repo.get_job(job_id)
            if not job: raise ValueError(f"Job {job_id} not found in DB.")
            
            job.status = "GENERATING_SCRIPT"
            await job_repo.update_job(job)

        try:
            script_data = await self.script_agent.execute(state["topic"])
            
            async with async_session() as session:
                job_repo = VideoJobRepository(session)
                job = await job_repo.get_job(job_id)
                job.title = script_data.title
                job.hook = script_data.hook
                job.full_script = script_data.full_script
                await job_repo.update_job(job)

            return {
                "title": script_data.title,
                "hook": script_data.hook,
                "full_script": script_data.full_script,
                "status": "GENERATING_SCRIPT"
            }
        except Exception as e:
            logger.error(f"Error in script_writing_node: {e}")
            return {"error": str(e)}

    async def scene_splitting_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: Scene Splitting ---")
        job_id = state["job_id"]
        
        async with async_session() as session:
            job_repo = VideoJobRepository(session)
            job = await job_repo.get_job(job_id)
            job.status = "GENERATING_SCENES"
            await job_repo.update_job(job)

        try:
            scenes_data = await self.scene_agent.execute(state["full_script"])
            
            scenes_list = []
            async with async_session() as session:
                scene_repo = SceneRepository(session)
                for s in scenes_data.scenes:
                    # Write to database
                    db_scene = await scene_repo.create_scene(
                        job_id=job_id,
                        scene_number=s.scene_number,
                        voice_text=s.voice_text,
                        video_prompt=s.visual_description, # Temporary visual prompt placeholder
                        duration=s.duration,
                        status="PENDING"
                    )
                    scenes_list.append({
                        "id": db_scene.id,
                        "scene_number": s.scene_number,
                        "voice_text": s.voice_text,
                        "visual_description": s.visual_description,
                        "duration": s.duration
                    })

            return {"scenes": scenes_list, "status": "GENERATING_SCENES"}
        except Exception as e:
            logger.error(f"Error in scene_splitting_node: {e}")
            return {"error": str(e)}

    async def scene_prompting_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: Scene Prompt Engineering ---")
        scenes = state["scenes"]
        updated_scenes = []
        
        try:
            async with async_session() as session:
                scene_repo = SceneRepository(session)
                for s in scenes:
                    # Formulate detailed visual prompts
                    prompt_out = await self.prompt_agent.execute(
                        scene_id=s["scene_number"],
                        visual_description=s["visual_description"]
                    )
                    # Update database scene
                    db_scene = await scene_repo.get_scene(s["id"])
                    if db_scene:
                        db_scene.video_prompt = prompt_out.video_prompt
                        db_scene.camera_motion = prompt_out.camera_motion
                        db_scene.lighting = prompt_out.lighting
                        db_scene.style = prompt_out.style
                        db_scene.negative_prompt = prompt_out.negative_prompt
                        await scene_repo.update_scene(db_scene)

                    s.update({
                        "video_prompt": prompt_out.video_prompt,
                        "camera_motion": prompt_out.camera_motion,
                        "lighting": prompt_out.lighting,
                        "style": prompt_out.style,
                        "negative_prompt": prompt_out.negative_prompt
                    })
                    updated_scenes.append(s)

            return {"scenes": updated_scenes}
        except Exception as e:
            logger.error(f"Error in scene_prompting_node: {e}")
            return {"error": str(e)}

    async def voice_narration_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: Voice Narration Structuring ---")
        scenes = state["scenes"]
        updated_scenes = []

        try:
            async with async_session() as session:
                scene_repo = SceneRepository(session)
                for s in scenes:
                    voice_out = await self.voice_agent.execute(s["scene_number"], s["voice_text"])
                    
                    db_scene = await scene_repo.get_scene(s["id"])
                    if db_scene:
                        db_scene.voice_text = voice_out.voice_text
                        db_scene.emotion = voice_out.emotion
                        # Save pauses as JSON string list
                        import json
                        db_scene.pause_points = json.dumps(voice_out.pause_points)
                        await scene_repo.update_scene(db_scene)

                    s.update({
                        "voice_text": voice_out.voice_text,
                        "emotion": voice_out.emotion,
                        "pause_points": voice_out.pause_points
                    })
                    updated_scenes.append(s)
            
            return {"scenes": updated_scenes}
        except Exception as e:
            logger.error(f"Error in voice_narration_node: {e}")
            return {"error": str(e)}

    async def video_generation_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: Google Flow Video Generation ---")
        job_id = state["job_id"]
        scenes = state["scenes"]
        updated_scenes = []

        async with async_session() as session:
            job_repo = VideoJobRepository(session)
            job = await job_repo.get_job(job_id)
            job.status = "GENERATING_MEDIA"
            await job_repo.update_job(job)

        try:
            # 1. Submit jobs and track IDs
            job_ids = []
            async with async_session() as session:
                scene_repo = SceneRepository(session)
                for s in scenes:
                    flow_job_id = await self.flow_service.submit_video_generation(
                        prompt=s["video_prompt"],
                        duration=s["duration"]
                    )
                    db_scene = await scene_repo.get_scene(s["id"])
                    if db_scene:
                        db_scene.flow_job_id = flow_job_id
                        db_scene.status = "SUBMITTED"
                        await scene_repo.update_scene(db_scene)
                    s["flow_job_id"] = flow_job_id
                    job_ids.append((s, flow_job_id))

            # 2. Wait and poll for operations
            logger.info("FlowAgent: Polling generated scene clips...")
            flow_agent = FlowAgent(self.flow_service)
            
            async with async_session() as session:
                scene_repo = SceneRepository(session)
                for item in job_ids:
                    s_dict, f_job_id = item
                    video_url = await flow_agent.wait_for_completion(f_job_id)
                    
                    # 3. Download the clip
                    video_filename = f"scene_{s_dict['scene_number']}.mp4"
                    local_video_path = str(settings.output_path / str(job_id) / "raw" / video_filename)
                    await flow_agent.download_video(video_url, local_video_path, s_dict["duration"])

                    db_scene = await scene_repo.get_scene(s_dict["id"])
                    if db_scene:
                        db_scene.video_url = video_url
                        db_scene.video_path = local_video_path
                        db_scene.status = "COMPLETED"
                        await scene_repo.update_scene(db_scene)
                    
                    s_dict["video_url"] = video_url
                    s_dict["video_path"] = local_video_path
                    updated_scenes.append(s_dict)

            return {"scenes": updated_scenes, "status": "GENERATING_MEDIA"}
        except Exception as e:
            logger.error(f"Error in video_generation_node: {e}")
            return {"error": str(e)}

    async def audio_generation_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: Voice Audio Generation ---")
        job_id = state["job_id"]
        scenes = state["scenes"]
        updated_scenes = []

        try:
            async with async_session() as session:
                scene_repo = SceneRepository(session)
                for s in scenes:
                    audio_filename = f"scene_{s['scene_number']}.wav"
                    local_audio_path = str(settings.output_path / str(job_id) / "audio" / audio_filename)
                    
                    # Call voice generation agent
                    await self.voice_gen_agent.generate_audio(
                        text=s["voice_text"],
                        dest_path=local_audio_path,
                        provider="openai",
                        voice="alloy",
                        emotion=s.get("emotion", "neutral"),
                        duration=s["duration"]
                    )

                    db_scene = await scene_repo.get_scene(s["id"])
                    if db_scene:
                        db_scene.audio_path = local_audio_path
                        await scene_repo.update_scene(db_scene)
                    
                    s["audio_path"] = local_audio_path
                    updated_scenes.append(s)

            return {"scenes": updated_scenes}
        except Exception as e:
            logger.error(f"Error in audio_generation_node: {e}")
            return {"error": str(e)}

    async def scene_compositing_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: Scene Compositing ---")
        job_id = state["job_id"]
        scenes = state["scenes"]
        updated_scenes = []

        try:
            for s in scenes:
                composite_filename = f"scene_{s['scene_number']}_composite.mp4"
                composite_path = str(settings.output_path / str(job_id) / "composites" / composite_filename)
                
                # Merge Video and Audio
                merged_path = await self.composer_agent.merge_scene(
                    video_path=s["video_path"],
                    audio_path=s["audio_path"],
                    output_path=composite_path
                )
                
                # Add Subtitles (overlay voice text)
                subtitled_filename = f"scene_{s['scene_number']}_subtitled.mp4"
                subtitled_path = str(settings.output_path / str(job_id) / "composites" / subtitled_filename)
                final_scene_path = await self.composer_agent.add_subtitles(
                    video_path=merged_path,
                    subtitles_text=s["voice_text"],
                    output_path=subtitled_path
                )
                
                s["composite_path"] = final_scene_path
                updated_scenes.append(s)

            return {"scenes": updated_scenes}
        except Exception as e:
            logger.error(f"Error in scene_compositing_node: {e}")
            return {"error": str(e)}

    async def final_video_assembly_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: Final Video Assembly ---")
        job_id = state["job_id"]
        scenes = state["scenes"]
        
        async with async_session() as session:
            job_repo = VideoJobRepository(session)
            job = await job_repo.get_job(job_id)
            job.status = "COMPOSING"
            await job_repo.update_job(job)

        try:
            scene_files = [s["composite_path"] for s in scenes]
            final_filename = "final_output.mp4"
            final_path = str(settings.output_path / str(job_id) / final_filename)
            
            # Combine scenes together
            await self.composer_agent.render_final_video(
                scene_video_paths=scene_files,
                output_path=final_path,
                background_music_path=None # Can pass local MP3 path if available
            )

            async with async_session() as session:
                job_repo = VideoJobRepository(session)
                job = await job_repo.get_job(job_id)
                job.final_video_path = final_path
                job.status = "COMPOSING"
                await job_repo.update_job(job)

            return {"final_video_path": final_path, "status": "COMPOSING"}
        except Exception as e:
            logger.error(f"Error in final_video_assembly_node: {e}")
            return {"error": str(e)}

    async def thumbnail_generation_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: Thumbnail Generation ---")
        job_id = state["job_id"]
        
        try:
            thumb_filename = "thumbnail.png"
            local_thumb_path = str(settings.output_path / str(job_id) / thumb_filename)
            
            design, path = await self.thumbnail_agent.execute(
                topic=state["topic"],
                hook=state["hook"],
                dest_path=local_thumb_path
            )

            async with async_session() as session:
                job_repo = VideoJobRepository(session)
                job = await job_repo.get_job(job_id)
                job.thumbnail_prompt = design.thumbnail_prompt
                job.thumbnail_path = path
                await job_repo.update_job(job)

            return {
                "thumbnail_prompt": design.thumbnail_prompt,
                "thumbnail_path": path
            }
        except Exception as e:
            logger.error(f"Error in thumbnail_generation_node: {e}")
            return {"error": str(e)}

    async def seo_optimization_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: SEO Optimization ---")
        job_id = state["job_id"]

        try:
            seo_data = await self.seo_agent.execute(
                topic=state["topic"],
                script=state["full_script"]
            )

            async with async_session() as session:
                job_repo = VideoJobRepository(session)
                job = await job_repo.get_job(job_id)
                job.youtube_title = seo_data.title
                job.youtube_description = seo_data.description
                job.youtube_tags = ",".join(seo_data.tags)
                await job_repo.update_job(job)

            return {
                "youtube_title": seo_data.title,
                "youtube_description": seo_data.description,
                "youtube_tags": seo_data.tags
            }
        except Exception as e:
            logger.error(f"Error in seo_optimization_node: {e}")
            return {"error": str(e)}

    async def youtube_upload_node(self, state: PipelineState) -> Dict[str, Any]:
        logger.info("--- NODE: YouTube Upload & Publish ---")
        job_id = state["job_id"]

        async with async_session() as session:
            job_repo = VideoJobRepository(session)
            job = await job_repo.get_job(job_id)
            job.status = "UPLOADING"
            await job_repo.update_job(job)

        try:
            # Run upload flow
            video_id = await self.youtube_agent.upload(
                video_path=state["final_video_path"],
                title=state["youtube_title"],
                description=state["youtube_description"],
                tags=state["youtube_tags"],
                thumbnail_path=state["thumbnail_path"],
                publish=False  # Uploads as private for safety review by default
            )

            async with async_session() as session:
                job_repo = VideoJobRepository(session)
                job = await job_repo.get_job(job_id)
                job.youtube_video_id = video_id
                job.status = "COMPLETED"
                await job_repo.update_job(job)

            return {"youtube_video_id": video_id, "status": "COMPLETED"}
        except Exception as e:
            logger.error(f"Error in youtube_upload_node: {e}")
            async with async_session() as session:
                job_repo = VideoJobRepository(session)
                job = await job_repo.get_job(job_id)
                job.status = "FAILED"
                job.error_message = str(e)
                await job_repo.update_job(job)
            return {"error": str(e), "status": "FAILED"}

    # --- EXECUTION ENTRYPOINT ---

    async def execute_pipeline(self, job_id: uuid.UUID, topic: str) -> Dict[str, Any]:
        """Execute the LangGraph state machine flow from end to end."""
        initial_state: PipelineState = {
            "job_id": job_id,
            "topic": topic,
            "status": "PENDING",
            "title": "",
            "hook": "",
            "full_script": "",
            "scenes": [],
            "final_video_path": "",
            "thumbnail_prompt": "",
            "thumbnail_path": "",
            "youtube_title": "",
            "youtube_description": "",
            "youtube_tags": [],
            "youtube_video_id": "",
            "error": ""
        }

        logger.info(f"Orchestrator: Executing workflow for job {job_id} on topic '{topic}'")
        final_state = await self.graph.ainvoke(initial_state)
        
        if final_state.get("error"):
            logger.error(f"Orchestrator: Finished with error: {final_state['error']}")
        else:
            logger.info(f"Orchestrator: Completed. YouTube Video ID: {final_state.get('youtube_video_id')}")
            
        return final_state

import os
import asyncio
from typing import List, Optional
from pathlib import Path
from loguru import logger

# Try importing MoviePy. Since MoviePy relies on FFmpeg and ImageMagick, we handle import issues gracefully.
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip
    from moviepy.audio.AudioClip import CompositeAudioClip
    import moviepy.video.fx.all as vfx
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

class ComposerAgent:
    def __init__(self):
        if not MOVIEPY_AVAILABLE:
            logger.warning("MoviePy is not installed or available. ComposerAgent will run in MOCK mode.")

    async def merge_scene(self, video_path: str, audio_path: str, output_path: str) -> str:
        """Combine scene video and audio, adjusting video duration to match audio length."""
        logger.info(f"ComposerAgent: Merging scene video {video_path} with audio {audio_path}")
        
        if not MOVIEPY_AVAILABLE:
            # Mock behavior: copy video_path to output_path if exists, otherwise write empty file
            await asyncio.sleep(1)
            if os.path.exists(video_path):
                import shutil
                shutil.copy(video_path, output_path)
            else:
                with open(output_path, "wb") as f:
                    f.write(b"")
            return output_path

        def _execute_merge():
            video = VideoFileClip(video_path)
            audio = AudioFileClip(audio_path)
            
            # Synchronize durations
            if video.duration < audio.duration:
                # Video is shorter than narration: loop the video
                logger.info(f"Looping video ({video.duration}s) to match audio narration duration ({audio.duration}s)")
                # MoviePy has a built-in loop fx
                video = video.fx(vfx.loop, duration=audio.duration)
            else:
                # Video is longer than narration: trim video to match audio
                logger.info(f"Trimming video ({video.duration}s) to match audio narration duration ({audio.duration}s)")
                video = video.subclip(0, audio.duration)
                
            video = video.set_audio(audio)
            
            # Write merged scene video
            video.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                logger=None
            )
            
            # Close files
            video.close()
            audio.close()
            return output_path

        try:
            return await asyncio.to_thread(_execute_merge)
        except Exception as e:
            logger.error(f"Error merging scene: {e}")
            raise e

    async def add_subtitles(self, video_path: str, subtitles_text: str, output_path: str) -> str:
        """Overlay subtitles/captions on a video file."""
        logger.info(f"ComposerAgent: Adding subtitles/text overlay to {video_path}")
        
        if not MOVIEPY_AVAILABLE:
            await asyncio.sleep(1)
            if os.path.exists(video_path):
                import shutil
                shutil.copy(video_path, output_path)
            return output_path

        def _execute_subtitles():
            video = VideoFileClip(video_path)
            
            try:
                # TextClip requires ImageMagick installed on system
                # We place the text overlay at the bottom center of the video
                txt_clip = TextClip(
                    subtitles_text,
                    fontsize=24,
                    color="white",
                    font="Arial",
                    stroke_color="black",
                    stroke_width=1,
                    size=(video.w * 0.8, None),
                    method="caption"
                )
                txt_clip = txt_clip.set_position(("center", "bottom")).set_duration(video.duration)
                
                # Composite the original video with the text clip
                result = CompositeVideoClip([video, txt_clip])
                result.write_videofile(
                    output_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    logger=None
                )
                txt_clip.close()
                result.close()
            except Exception as magick_err:
                logger.warning(
                    f"ImageMagick not configured/found on host system ({magick_err}). "
                    f"Skipping subtitle overlay rendering. Returning original merged video."
                )
                # If ImageMagick is missing, copy original video to output path instead of failing
                import shutil
                shutil.copy(video_path, output_path)
            
            video.close()
            return output_path

        try:
            return await asyncio.to_thread(_execute_subtitles)
        except Exception as e:
            logger.error(f"Error adding subtitles: {e}")
            raise e

    async def render_final_video(self, scene_video_paths: List[str], output_path: str, background_music_path: Optional[str] = None) -> str:
        """Merge all individual scene videos into one final video, mixing background music if provided."""
        logger.info(f"ComposerAgent: Rendering final video concatenation from {len(scene_video_paths)} scenes")
        
        if not MOVIEPY_AVAILABLE:
            await asyncio.sleep(2)
            # Make sure parent directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"MOCK VIDEO DATA")
            return output_path

        def _execute_render():
            clips = [VideoFileClip(p) for p in scene_video_paths if os.path.exists(p)]
            if not clips:
                raise ValueError("No valid scene video paths found to concatenate.")
                
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Mix Background Music if provided
            if background_music_path and os.path.exists(background_music_path):
                logger.info(f"Mixing background music: {background_music_path}")
                bg_music = AudioFileClip(background_music_path)
                
                # Loop bg music if shorter than video, or trim if longer
                if bg_music.duration < final_clip.duration:
                    bg_music = bg_music.fx(vfx.loop, duration=final_clip.duration)
                else:
                    bg_music = bg_music.subclip(0, final_clip.duration)
                
                # Soften background music volume (e.g. to 15%) so voiceover is clear
                bg_music = bg_music.volumex(0.15)
                
                original_audio = final_clip.audio
                if original_audio:
                    # Mix voiceover with background music
                    mixed_audio = CompositeAudioClip([original_audio, bg_music])
                    final_clip.audio = mixed_audio
                else:
                    final_clip.audio = bg_music

            final_clip.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                logger=None
            )
            
            # Clean up clips
            for c in clips:
                c.close()
            final_clip.close()
            return output_path

        try:
            return await asyncio.to_thread(_execute_render)
        except Exception as e:
            logger.error(f"Error rendering final video: {e}")
            raise e

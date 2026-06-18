import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel

# Import agents and schemas
from agents.script_agent import ScriptAgent, ScriptOutput
from agents.scene_agent import SceneAgent, SceneSplitterOutput, SceneDetail
from agents.prompt_agent import PromptAgent, PromptOutput
from agents.voice_agent import VoiceAgent, VoiceOutput

@pytest.mark.asyncio
async def test_script_agent():
    # Mock OpenAIService
    mock_openai = MagicMock()
    mock_openai.generate_structured_json = AsyncMock(return_value=ScriptOutput(
        title="Mock Title",
        hook="Mock Hook",
        full_script="Mock script body content."
    ))
    
    agent = ScriptAgent(mock_openai)
    result = await agent.execute("AI future")
    
    assert result.title == "Mock Title"
    assert result.hook == "Mock Hook"
    assert result.full_script == "Mock script body content."
    mock_openai.generate_structured_json.assert_called_once()

@pytest.mark.asyncio
async def test_scene_splitter_agent():
    mock_openai = MagicMock()
    mock_openai.generate_structured_json = AsyncMock(return_value=SceneSplitterOutput(
        scenes=[
            SceneDetail(
                scene_number=1,
                voice_text="Script voiceover segment",
                visual_description="Visual details",
                duration=4.5
            )
        ]
    ))
    
    agent = SceneAgent(mock_openai)
    result = await agent.execute("Continuous script content")
    
    assert len(result.scenes) == 1
    assert result.scenes[0].scene_number == 1
    assert result.scenes[0].duration == 4.5
    mock_openai.generate_structured_json.assert_called_once()

@pytest.mark.asyncio
async def test_prompt_agent():
    mock_openai = MagicMock()
    mock_openai.generate_structured_json = AsyncMock(return_value=PromptOutput(
        scene_id=2,
        video_prompt="Cinematic neon glowing city",
        camera_motion="slow zoom out",
        lighting="neon",
        style="photorealistic",
        negative_prompt="blurry"
    ))
    
    agent = PromptAgent(mock_openai)
    result = await agent.execute(2, "neon glowing city visual description")
    
    assert result.scene_id == 2
    assert result.video_prompt == "Cinematic neon glowing city"
    assert result.camera_motion == "slow zoom out"
    mock_openai.generate_structured_json.assert_called_once()

@pytest.mark.asyncio
async def test_voice_agent_narration():
    mock_openai = MagicMock()
    mock_openai.generate_structured_json = AsyncMock(return_value=VoiceOutput(
        scene_id=1,
        voice_text="Formatted narration block.",
        emotion="energetic",
        pause_points=[1.5, 3.0]
    ))
    
    agent = VoiceAgent(mock_openai)
    result = await agent.execute(1, "raw voice text segment")
    
    assert result.scene_id == 1
    assert result.voice_text == "Formatted narration block."
    assert result.emotion == "energetic"
    assert result.pause_points == [1.5, 3.0]
    mock_openai.generate_structured_json.assert_called_once()

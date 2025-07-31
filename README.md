# Voice Agent with AssemblyAI's Universal-Streaming real-time API, OpenAI, and ElevenLabs

🔑 **[Get your AssemblyAI API key](https://www.assemblyai.com/dashboard/signup)** - Access to Universal-Streaming + $50 credits

Build an ultra-low latency AI voice agent using AssemblyAI's new Universal-Streaming API, OpenAI GPT-4, and ElevenLabs voice synthesis.

## 📋 Prerequisites

- Python 3.8+
- API keys: [AssemblyAI](https://www.assemblyai.com), [OpenAI](https://platform.openai.com), [ElevenLabs](https://elevenlabs.io)

## 🛠️ Quick Start

1. **Clone & Install**
```bash
git clone git@github.com:gsharp-aai/voice-agent-aai-elevenlabs-openai.git
cd voice-agent-aai-elevenlabs-openai
pip install assemblyai openai elevenlabs python-dotenv
```

2. **Add API Keys**
```python
self.assemblyai_api_key = "ASSEMBLYAI_API_KEY" # Replace with your actual AssemblyAI API key
self.openai_client = OpenAI(api_key="OPEN_AI_API_KEY")  # Replace with your actual OpenAI API key
self.elevenlabs_api_key = "ELEVEN_LABS_API_KEY"  # Replace with your actual ElevenLabs API key
```

3. **Toggle Debug Logging**
Most logging is turned off for this tutorial to show a clean transcript output.
If you'd like to see errors, session data, and other information in console, simply change the `DEBUG_MODE` variable. 
```python
DEBUG_MODE = False  # Set to True to see all logs and debug messages
```

4. Run
```bash
python main.py
```

📚 Resources

[Universal-Streaming Docs](https://www.assemblyai.com/docs/speech-to-text/universal-streaming)

[Voice Agent Guide](https://www.assemblyai.com/docs/speech-to-text/universal-streaming#voice-agent-use-case)

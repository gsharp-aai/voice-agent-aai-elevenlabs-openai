import assemblyai as aai
from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    TerminationEvent,
    TurnEvent,
)
from elevenlabs import ElevenLabs, play, VoiceSettings
from openai import OpenAI
import logging
from typing import Type

# Configuration
DEBUG_MODE = False  # Set to True to see all logs and debug messages

# Configure logging based on DEBUG_MODE
if DEBUG_MODE:
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.CRITICAL)  # Suppress all logs except critical
    # Also suppress HTTP logs from libraries for clean conversation output
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore").setLevel(logging.CRITICAL)
    logging.getLogger("openai").setLevel(logging.CRITICAL)
    logging.getLogger("elevenlabs").setLevel(logging.CRITICAL)
    
logger = logging.getLogger(__name__)


class AI_Assistant:
    def __init__(self):
        # API Keys - Use python-dotenv or similar to manage these securely in production.        
        self.assemblyai_api_key = "ASSEMBLYAI_API_KEY" # Replace with your actual AssemblyAI API key
        self.openai_client = OpenAI(api_key="OPEN_AI_API_KEY")  # Replace with your actual OpenAI API key
        self.elevenlabs_api_key = "ELEVEN_LABS_API_KEY"  # Replace with your actual ElevenLabs API key
        
        # Initialize ElevenLabs client
        self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
        
        self.client = None
        self.microphone_stream = None
        
        # Prompt
        self.full_transcript = [
            {"role": "system", "content": "You are a receptionist at a dental clinic. Be resourceful and efficient."},
        ]
        
        # Track conversation state for latency optimization
        self.is_processing = False
        self.running_transcript = ""  # Accumulates finalized transcripts
        self.latest_partial = ""      # Current partial transcript
        self.should_process_on_next_final = False  # Flag to process when we see end_of_turn
        
        # Store reference to AI assistant for use in callbacks
        global ai_assistant_instance
        ai_assistant_instance = self

    ###### Step 2: Real-Time Transcription with AssemblyAI Universal-Streaming ######

    def start_transcription(self):
        # Create the streaming client
        self.client = StreamingClient(
            StreamingClientOptions(
                api_key=self.assemblyai_api_key,
                api_host="streaming.assemblyai.com",
            )
        )
        
        # Set up event handlers
        self.client.on(StreamingEvents.Begin, on_begin)
        self.client.on(StreamingEvents.Turn, on_turn)
        self.client.on(StreamingEvents.Termination, on_terminated)
        self.client.on(StreamingEvents.Error, on_error)
        
        # Connect with parameters
        self.client.connect(
            StreamingParameters(
                sample_rate=16000,
                format_turns=False,  # Disabled for lowest latency
                end_of_turn_confidence_threshold=0.7,
                min_end_of_turn_silence_when_confident=160,
                max_turn_silence=2400,
            )
        )
        
        # Start streaming from microphone
        self.microphone_stream = aai.extras.MicrophoneStream(sample_rate=16000)
        self.client.stream(self.microphone_stream)

    def stop_transcription(self):
        if self.client:
            self.client.disconnect(terminate=True)
            self.client = None
        if self.microphone_stream:
            self.microphone_stream = None

    def process_turn(self):
        """Process the accumulated transcript following AssemblyAI's recommended strategy"""
        # Combine running transcript with latest partial
        complete_text = self.running_transcript
        if self.latest_partial:
            if complete_text:
                complete_text += " " + self.latest_partial
            else:
                complete_text = self.latest_partial
        
        # Clear running_transcript
        self.running_transcript = ""
        # Note: We keep latest_partial as it will become final later
        
        # Process with LLM
        if complete_text.strip():
            self.generate_ai_response(complete_text)

    def generate_ai_response(self, transcript_text):
        self.is_processing = True
        self.stop_transcription()
        
        self.full_transcript.append({"role": "user", "content": transcript_text})
        print(f"\nPatient: {transcript_text}\n")
        
        # Stream the response from OpenAI
        stream = self.openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=self.full_transcript,
            stream=True  # Enable streaming
        )
        
        # Print AI response header
        print(f"AI Receptionist: ", end="", flush=True)
        
        # Collect the full response while streaming
        ai_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                ai_response += content
                print(content, end="", flush=True)  # Print as it streams
        
        print()  # New line after streaming completes
        
        # Generate audio with the complete response
        self.generate_audio(ai_response)
        
        self.is_processing = False
        # Reset state before restarting
        self.running_transcript = ""
        self.latest_partial = ""
        self.should_process_on_next_final = False
        
        self.start_transcription()

    ###### Step 4: Generate audio with ElevenLabs ######

    def generate_audio(self, text):
        self.full_transcript.append({"role": "assistant", "content": text})
        
        # Generate audio using the new ElevenLabs API
        audio = self.elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id="pNInz6obpgDQGcFmaJgB",
            output_format="mp3_22050_32",
            model_id="eleven_turbo_v2_5",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
                speed=1.0,
            ),
        )
        
        # Play the audio
        play(audio)


# Global variable to access AI assistant instance from callbacks
ai_assistant_instance = None

# Event handler functions following SDK pattern
def on_begin(self: Type[StreamingClient], event: BeginEvent):
    if DEBUG_MODE:
        logger.info(f"Session started: {event.id}")
        print(f"Session ID: {event.id}")
    print("\n[Listening... Start speaking]")

def on_turn(self: Type[StreamingClient], event: TurnEvent):
    if not event.transcript or ai_assistant_instance.is_processing:
        return
    
    # Always update latest partial and show real-time transcription
    ai_assistant_instance.latest_partial = event.transcript
    print(f"\r{event.transcript}", end='', flush=True)
    
    # Check if this is marked as end of turn
    if event.end_of_turn:
        if ai_assistant_instance.should_process_on_next_final:
            # This is the final for the partial we already processed - ignore it
            ai_assistant_instance.should_process_on_next_final = False
            # Clear latest_partial since it was already included in the LLM call
            ai_assistant_instance.latest_partial = ""
        else:
            # This is a new final - process immediately for lowest latency
            ai_assistant_instance.should_process_on_next_final = True
            ai_assistant_instance.process_turn()

def on_terminated(self: Type[StreamingClient], event: TerminationEvent):
    if DEBUG_MODE:
        logger.info(f"Session terminated: {event.audio_duration_seconds} seconds of audio processed")

def on_error(self: Type[StreamingClient], error: StreamingError):
    if DEBUG_MODE:
        print(f"An error occurred: {error}")
        logger.error(f"Streaming error: {error}")


# Main execution
if __name__ == "__main__":
    greeting = "Thank you for calling Vancouver dental clinic. My name is Sonny, how may I assist you?"
    print(f"AI Receptionist: {greeting}")  # Print the initial greeting
    ai_assistant = AI_Assistant()
    ai_assistant.generate_audio(greeting)
    
    try:
        ai_assistant.start_transcription()
        # Keep the program running
        if DEBUG_MODE:
            input("Press Enter to stop...\n")
        else:
            input()  # Silent input wait
    except KeyboardInterrupt:
        if DEBUG_MODE:
            print("\nStopping...")
    finally:
        ai_assistant.stop_transcription()
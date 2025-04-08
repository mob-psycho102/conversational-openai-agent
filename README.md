# Vocabulary Practice App with Siri-like Interface

A voice-based application to practice English vocabulary with a floating Siri-like interface. The app selects random words from a word list, asks you to explain them, and provides feedback through OpenAI's GPT-4o.

## Features

- Sleek floating bubble interface inspired by Siri
- Voice input and output
- Real-time feedback on word explanations using GPT-4o
- Customizable word list
- Animated visual feedback for listening, processing, and speaking

## Requirements

- Python 3.8+
- OpenAI API key
- Microphone and speakers

## Installation

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Download the Vosk speech recognition model:
   ```
   # Download the small English model (about 40MB)
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   ```

3. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

4. Create or modify the `words_list.csv` file with your preferred vocabulary words:
   ```
   word
   serendipity
   ephemeral
   ubiquitous
   ...
   ```

## Usage

Run the application:
```
python main.py
```

### Voice Commands

- **"That's my explanation"**: End your current explanation and get feedback
- **"Change word please"**: Skip the current word and get a new one
- **"End this conversation please"**: Exit the application

### User Interface

- **Drag**: Move the bubble interface anywhere on your screen
- **Double-click**: Toggle between expanded and collapsed views

## Customization

- Edit `instructions` in `main.py` to change the voice style
- Modify the `words_list.csv` file to add your own vocabulary words
- Adjust colors and animations in `siri_bubble.py`

## Troubleshooting

- **Audio issues**: Make sure your microphone and speakers are properly configured
- **API errors**: Check your OpenAI API key in the `.env` file
- **Vosk model errors**: Ensure the model path is correctly set in the code

## Credits

- Uses OpenAI's GPT-4o for NLP and text generation
- Voice recognition powered by Vosk
- UI built with PySide6 (Qt for Python)
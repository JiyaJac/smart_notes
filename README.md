<p align="center">
  <img src="./img.png" alt="Project Banner" width="100%">
</p>

# SmartNotes 🎯

## Basic Details

### Team Name: Stack

### Team Members
- Member 1: Jiya Mary Jacob - Model Engineering college
- Member 2: Joylin Alex - Model Engineering college

### Hosted Project Link
https://smart-notes-xe6l.vercel.app/

### Project Description
“Academic Notes Analyzer: A Flask + HTML app with an AI assistant that evaluates student notes, generates flashcards, quizzes, and mindmap summaries, providing personalized feedback to highlight strengths, weaknesses, and study suggestions for smarter learning.”

### The Problem statement
Students often take notes in various formats and styles, but the effectiveness of these notes varies widely due to inconsistencies, missing concepts, and poor structure. This makes it difficult for students to evaluate the quality of their notes, identify gaps in their learning, and revise efficiently.

### The Solution
 SmartNotes addresses this challenge by using artificial intelligence and natural language processing to analyze and assess the clarity, completeness, and structure of student notes. The system compares notes against syllabus standards or reference materials, highlights missing topics, and generates personalized flashcards and quizzes for effective revision. By providing actionable feedback and interactive learning resources, SmartNotes helps students study smarter, retain knowledge better, and improve overall academic performance.

---

## Technical Details

### Technologies/Components Used

**For Software:**
- Languages used: Python, HTML, CSS, JavaScript
- Frameworks used: Flask  
- Libraries used:  Groq, Flask-CORS, python-dotenv, Jinja2  
- Tools used: VS Code, Git, Vercel (for deployment)

---

## Features

List the key features of your project:
- **Notes Analysis:** Evaluate notes for completeness, clarity, structure, and topic coverage using AI.  
- **Flashcard Generation:** Create 10 AI-powered flashcards from notes with easy, medium, and hard difficulty.  
- **Quiz Creation & Evaluation:** Generate 8 multiple-choice questions and evaluate answers, highlighting weak and strong topics.  
- **Mindmap Summary:** Automatically generate a mindmap summary for quick revision.  
- **AI Assistant:** Provides personalized suggestions, improvements, and study guidance.  
- **Frontend:** HTML/CSS/JS interface for submitting notes and viewing analysis, flashcards, quizzes, and summaries.  

---

## Implementation

### For Software:

#### Installation
```bash
# Clone the repository
git clone https://github.com/JiyaJac/smartnotes.git
cd smartnotes/backend

# Install Python dependencies
pip install -r requirements.txt

# create .env file for API key
echo "GROQ_API_KEY=your_api_key_here" > .env
```

#### Run
```bash
# Run the Flask backend

python app.py
```
Open http://localhost:10000 to access the HTML frontend.



---

## Project Documentation

### For Software:

#### Screenshots (Add at least 3)

 <img src="./1.png">
 <img src="./2.png">
 <img src="./3.png">
 <img src="./4.png">
 <img src="./5.png">

**evaluating various diffrent notes with the reference syllabus and generating a scoring system**
 
 
 
 <img src="./6.png">
 <img src="./7.png">
 <img src="./8.png">

 **generating flash cards based on the input content**



 <img src="./9.png">
 <img src="./10.png">
 <img src="./11.png">
 <img src="./12.png">

 **generating quiz questions bassed on the topic. The answers are then evaluated and the weak areas are identified suggesting appropriate improvement.**



 
 <img src="./13.png">
 <img src="./14.png">
 <img src="./15.png">
 <img src="./16.png">
 <img src="./17.png">

 **generating summary along with mind maps based on user preference.**

 <img src="./18.png">
 
**chatting with an ai on topics related to the content uploaded.**

 
#### Diagrams

**System Architecture:**

<img src="./19.png">
*Explain your system architecture - components, data flow, tech stack interaction*

**Application Workflow:**

<img src="./20.png">
<img src="./21.png">
*Add caption explaining your workflow*

---

### For Hardware:

#### Schematic & Circuit

![Circuit](Add your circuit diagram here)
*Add caption explaining connections*

![Schematic](Add your schematic diagram here)
*Add caption explaining the schematic*

#### Build Photos

![Team](Add photo of your team here)

![Components](Add photo of your components here)
*List out all components shown*

![Build](Add photos of build process here)
*Explain the build steps*

![Final](Add photo of final product here)
*Explain the final build*

---

## Additional Documentation

### For Web Projects with Backend:

#### API Documentation

**Base URL:** 'https://smart-notes-xe6l.vercel.app/'

##### Endpoints

**GET /api/endpoint**
- **Description:** Submits student notes for analysis. Returns a JSON report with completeness, clarity, structure, strengths, weaknesses, and improvement suggestions.
- **Parameters:**
1. Analyze Notes (POST /api/analyze)
Parameters (in request body JSON):
notes (string): The content of the student’s notes to analyze. Required.
subject (string, optional): The subject or topic context for more accurate analysis.
2. Generate Flashcards (POST /api/flashcards)
Parameters (in request body JSON):
notes (string): The student notes to generate flashcards from. Required.
num_flashcards (integer): Number of flashcards to generate. Default is 10.
3. Generate Quiz (POST /api/quiz)
Parameters (in request body JSON):
notes (string): Notes used to generate quiz questions. Required.
num_questions (integer): Number of multiple-choice questions to generate. Default is 8.
4. Evaluate Quiz (POST /api/evaluate-quiz)
Parameters (in request body JSON):
quiz_id (string): Unique ID of the quiz being evaluated. Required.
answers (array of strings): User’s selected answers in order corresponding to quiz questions. Required.
- **Response:**
{
  "status": "success",
  "data": {
    "overall_score": 87,
    "topic_coverage": {
      "topic1": "complete",
      "topic2": "partial",
      "topic3": "missing"
    },
    "strengths": ["topic1", "topic4"],
    "weaknesses": ["topic2"],
    "suggestions": ["Expand topic2 with examples", "Organize topic3"]
  }
}
{
  "status": "success",
  "data": [
    {
      "question": "What is X?",
      "answer": "X is ...",
      "difficulty": "easy"
    },
    {
      "question": "Explain Y.",
      "answer": "Y is ...",
      "difficulty": "medium"
    }
  ]
{
  "status": "success",
  "data": [
    {
      "question": "What is Z?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option B",
      "topic": "Topic3",
      "difficulty": "hard"
    }
  ]
{
  "status": "success",
  "data": {
    "score": 6,
    "total_questions": 8,
    "weak_topics": ["Topic2"],
    "strong_topics": ["Topic1", "Topic4"],
    "recommendations": ["Review Topic2 concepts", "Revise examples from Topic3"]
  }
}
**POST /api/endpoint**
- **Description:** Submits student notes for AI analysis and returns a report with completeness, clarity, strengths, weaknesses, and improvement suggestions.
- **Request Body:**
```json
{
  "notes": "Content of student's notes",
  "subject": "Optional subject or topic for context"
}
```
- **Response:**
```json
{
  "status": "success",
  "data": {
    "overall_score": 87,
    "topic_coverage": {
      "topic1": "complete",
      "topic2": "partial",
      "topic3": "missing"
    },
    "strengths": ["topic1", "topic4"],
    "weaknesses": ["topic2"],
    "suggestions": ["Expand topic2 with examples", "Organize topic3"]
  }
}
```

[Add more endpoints as needed...]

---

### For Mobile Apps:

#### App Flow Diagram

![App Flow](docs/app-flow.png)
*Explain the user flow through your application*

#### Installation Guide

**For Android (APK):**
1. Download the APK from [Release Link]
2. Enable "Install from Unknown Sources" in your device settings:
   - Go to Settings > Security
   - Enable "Unknown Sources"
3. Open the downloaded APK file
4. Follow the installation prompts
5. Open the app and enjoy!

**For iOS (IPA) - TestFlight:**
1. Download TestFlight from the App Store
2. Open this TestFlight link: [Your TestFlight Link]
3. Click "Install" or "Accept"
4. Wait for the app to install
5. Open the app from your home screen

**Building from Source:**
```bash
# For Android
flutter build apk
# or
./gradlew assembleDebug

# For iOS
flutter build ios
# or
xcodebuild -workspace App.xcworkspace -scheme App -configuration Debug
```

---

### For Hardware Projects:

#### Bill of Materials (BOM)

| Component | Quantity | Specifications | Price | Link/Source |
|-----------|----------|----------------|-------|-------------|
| Arduino Uno | 1 | ATmega328P, 16MHz | ₹450 | [Link] |
| LED | 5 | Red, 5mm, 20mA | ₹5 each | [Link] |
| Resistor | 5 | 220Ω, 1/4W | ₹1 each | [Link] |
| Breadboard | 1 | 830 points | ₹100 | [Link] |
| Jumper Wires | 20 | Male-to-Male | ₹50 | [Link] |
| [Add more...] | | | | |

**Total Estimated Cost:** ₹[Amount]

#### Assembly Instructions

**Step 1: Prepare Components**
1. Gather all components listed in the BOM
2. Check component specifications
3. Prepare your workspace
![Step 1](images/assembly-step1.jpg)
*Caption: All components laid out*

**Step 2: Build the Power Supply**
1. Connect the power rails on the breadboard
2. Connect Arduino 5V to breadboard positive rail
3. Connect Arduino GND to breadboard negative rail
![Step 2](images/assembly-step2.jpg)
*Caption: Power connections completed*

**Step 3: Add Components**
1. Place LEDs on breadboard
2. Connect resistors in series with LEDs
3. Connect LED cathodes to GND
4. Connect LED anodes to Arduino digital pins (2-6)
![Step 3](images/assembly-step3.jpg)
*Caption: LED circuit assembled*

**Step 4: [Continue for all steps...]**

**Final Assembly:**
![Final Build](images/final-build.jpg)
*Caption: Completed project ready for testing*

---

### For Scripts/CLI Tools:

#### Command Reference

**Basic Usage:**
```bash
python script.py [options] [arguments]
```

**Available Commands:**
- `command1 [args]` - Description of what command1 does
- `command2 [args]` - Description of what command2 does
- `command3 [args]` - Description of what command3 does

**Options:**
- `-h, --help` - Show help message and exit
- `-v, --verbose` - Enable verbose output
- `-o, --output FILE` - Specify output file path
- `-c, --config FILE` - Specify configuration file
- `--version` - Show version information

**Examples:**

```bash
# Example 1: Basic usage
python script.py input.txt

# Example 2: With verbose output
python script.py -v input.txt

# Example 3: Specify output file
python script.py -o output.txt input.txt

# Example 4: Using configuration
python script.py -c config.json --verbose input.txt
```

#### Demo Output

**Example 1: Basic Processing**

**Input:**
```
This is a sample input file
with multiple lines of text
for demonstration purposes
```

**Command:**
```bash
python script.py sample.txt
```

**Output:**
```
Processing: sample.txt
Lines processed: 3
Characters counted: 86
Status: Success
Output saved to: output.txt
```

**Example 2: Advanced Usage**

**Input:**
```json
{
  "name": "test",
  "value": 123
}
```

**Command:**
```bash
python script.py -v --format json data.json
```

**Output:**
```
[VERBOSE] Loading configuration...
[VERBOSE] Parsing JSON input...
[VERBOSE] Processing data...
{
  "status": "success",
  "processed": true,
  "result": {
    "name": "test",
    "value": 123,
    "timestamp": "2024-02-07T10:30:00"
  }
}
[VERBOSE] Operation completed in 0.23s
```

---

## Project Demo

### Video
[Add your demo video link here - YouTube, Google Drive, etc.]

*Explain what the video demonstrates - key features, user flow, technical highlights*

### Additional Demos
[Add any extra demo materials/links - Live site, APK download, online demo, etc.]

---

## AI Tools Used (Optional - For Transparency Bonus)

If you used AI tools during development, document them here for transparency:

**Tool Used:** [e.g., GitHub Copilot, v0.dev, Cursor, ChatGPT, Claude]

**Purpose:** [What you used it for]
- Example: "Generated boilerplate React components"
- Example: "Debugging assistance for async functions"
- Example: "Code review and optimization suggestions"

**Key Prompts Used:**
- "Create a REST API endpoint for user authentication"
- "Debug this async function that's causing race conditions"
- "Optimize this database query for better performance"

**Percentage of AI-generated code:** [Approximately X%]

**Human Contributions:**
- Architecture design and planning
- Custom business logic implementation
- Integration and testing
- UI/UX design decisions

*Note: Proper documentation of AI usage demonstrates transparency and earns bonus points in evaluation!*

---

## Team Contributions

- [Name 1]: [Specific contributions - e.g., Frontend development, API integration, etc.]
- [Name 2]: [Specific contributions - e.g., Backend development, Database design, etc.]
- [Name 3]: [Specific contributions - e.g., UI/UX design, Testing, Documentation, etc.]

---

## License

This project is licensed under the [LICENSE_NAME] License - see the [LICENSE](LICENSE) file for details.

**Common License Options:**
- MIT License (Permissive, widely used)
- Apache 2.0 (Permissive with patent grant)
- GPL v3 (Copyleft, requires derivative works to be open source)

---

Made with ❤️ at TinkerHub

Our MVP is a morning planner that tells you what programming task to start and helps you fit it around your courier shift and gym. Its success is whether it helps you start useful work with less deciding.
MVP feature	What it does	Where we are
Concrete project plan	Tasks have deliverables, first actions, completion checks, prerequisites, and time estimates	Basic structure built
Saved progress	Remembers completed tasks between sessions	Built
Task selection	Chooses an unfinished task whose prerequisites are complete and that fits your time	Working on this
Morning schedule	Uses your work start time to fit your morning routine, programming, and gym; flags when everything won’t fit	Not built
Continuation note	Saves where you stopped and what to do first next session	Not built
Simple dashboard	Shows the plan and lets you update progress	First version built


For the MVP, we write the project’s learning plan together and load it into the app. It doesn’t need automatic plan generation to be useful.
The fuller version we’re aiming toward would help you go from “I want to learn/build this” to a realistic daily plan:
- Explain the stack in plain language, including why each technology fits.
- Produce concrete deliverables, sequenced so each builds on the last.
- Break milestones into sessions suited to your available time.
- Carry unfinished work forward and use your continuation notes.
- Adjust future estimates using how long tasks actually took.
- Let you review and change the plan before following it.
We’d add those features based on what you find useful while using the MVP.
The next milestone is one complete morning: enter when work starts → get a feasible schedule and programming task → do the session → save progress and tomorrow’s starting point. That’s the outcome our remaining backend work should serve.





Its core idea is:
AI can write the code, but the learner must become capable of directing, reading, explaining, and verifying it.

It combines:
- Building one real project with Codex or Claude Code.
- A coaching layer that questions your understanding.
- A finite project journey with sections and tasks.
- A knowledge graph of concepts you’ve encountered.
- Evidence that you understand each concept.
- Quizzes and spaced repetition when knowledge starts fading.
- Clear tracking of what you shipped, what comes next, and what remains locked.
The important difference is that Altitude is primarily a coding-learning system, while our app began as a daily execution system. Morning Plan answers “What should I work on today, and how do I begin?” Altitude answers “Do I understand what the coding agent built?”
There is a strong opportunity to combine those ideas without copying the entire product. After each focus session, our app could ask:
1. What did you build?
2. How does it work?
3. What concept did you use?
4. What evidence proves it works?
5. What is the exact next action?
A task would then have three separate states:
Implemented → Tested → Understood
That is stronger than marking something “completed” because the program ran once.
For our product, I would prioritize:
- Session history and heatmap.
- End-of-session reflection and continuation.
- Evidence attached to completed tasks.
- A short understanding checkpoint before completion.
- Later, a concept map showing what you understand and what needs review.
Altitude validates that our concern is real: AI makes building faster, but it can also let you finish projects without developing the mental model needed for internships and debugging. Our app can address that while remaining more focused on your daily routine, procrastination, and starting work consistently.